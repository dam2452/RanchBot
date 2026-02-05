import json
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from elastic_transport import ObjectApiResponse

from bot.search.elastic_search_manager import ElasticSearchManager
from bot.settings import settings
from bot.utils.log import log_system_message


class TranscriptionFinder:
    @staticmethod
    def is_segment_overlap(
            previous_segment: json,
            segment: json,
            start_time: float,
    ) -> bool:

        return (
                previous_segment and
                previous_segment.get("episode_metadata", {}).get("season") == segment["episode_metadata"]["season"] and
                previous_segment.get("episode_metadata", {}).get("episode_number") == segment["episode_metadata"][
                    "episode_number"
                ] and
                start_time <= previous_segment.get("end_time", previous_segment.get("end", 0))
        )

    @staticmethod
    def _merge_overlapping_segment(segment: Dict[str, Any], unique_segments: List[Dict[str, Any]], start_time: float, end_time: float) -> bool:
        for i, existing_segment in enumerate(unique_segments):
            existing_start = existing_segment["start_time"] - settings.EXTEND_BEFORE
            existing_end = existing_segment["end_time"] + settings.EXTEND_AFTER

            if (
                segment.get("episode_metadata", {}).get("season") == existing_segment.get("episode_metadata", {}).get("season") and
                segment.get("episode_metadata", {}).get("episode_number") == existing_segment.get("episode_metadata", {}).get("episode_number") and
                start_time <= existing_end and end_time >= existing_start
            ):
                unique_segments[i]["start_time"] = min(existing_segment["start_time"], segment["start_time"])
                unique_segments[i]["end_time"] = max(existing_segment["end_time"], segment["end_time"])
                unique_segments[i]["_score"] = max(existing_segment.get("_score", 0), segment.get("_score", 0))
                return True
        return False

    @staticmethod
    async def find_segment_by_quote(
            quote: str, logger: logging.Logger, series_name: str, season_filter: Optional[int] = None,
            episode_filter: Optional[int] = None,
            size: int = 1,
    ) -> Optional[Union[List[ObjectApiResponse], ObjectApiResponse]]:
        await log_system_message(
            logging.INFO,
            f"Searching for quote: '{quote}' in series '{series_name}' with filters - Season: {season_filter}, Episode: {episode_filter}",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        index = f"{series_name}_text_segments"

        query = {
            "query": {
                "bool": {
                    "must": {
                        "match": {
                            "text": {
                                "query": quote,
                                "fuzziness": "AUTO",
                            },
                        },
                    },
                    "filter": [
                        {"term": {"episode_metadata.series_name": series_name}},
                    ],
                },
            },
            "sort": [
                {"episode_metadata.season": "asc"},
                {"episode_metadata.episode_number": "asc"},
                {"start_time": "asc"},
            ],
        }

        if season_filter:
            query["query"]["bool"]["filter"].append({"term": {"episode_metadata.season": season_filter}})

        if episode_filter:
            query["query"]["bool"]["filter"].append({"term": {"episode_metadata.episode_number": episode_filter}})

        hits = (await es.search(index=index, body=query, size=size))["hits"]["hits"]

        if not hits:
            await log_system_message(logging.INFO, "No segments found matching the query.", logger)
            return None

        unique_segments = []
        seen_segments = set()

        for hit in hits:
            segment = hit["_source"]
            segment["_score"] = hit["_score"]
            segment_key = (
                segment.get("episode_metadata", {}).get("season"),
                segment.get("episode_metadata", {}).get("episode_number"),
                segment.get("start_time"),
                segment.get("end_time"),
            )

            if segment_key not in seen_segments:
                seen_segments.add(segment_key)

                start_time = segment["start_time"] - settings.EXTEND_BEFORE
                end_time = segment["end_time"] + settings.EXTEND_AFTER

                is_overlapping = TranscriptionFinder._merge_overlapping_segment(segment, unique_segments, start_time, end_time)

                if not is_overlapping:
                    unique_segments.append(segment)

        unique_segments.sort(key=lambda x: x.get("_score", 0), reverse=True)

        await log_system_message(
            logging.INFO, f"Found {len(unique_segments)} unique segments after merging.",
            logger,
        )

        if unique_segments:
            return unique_segments[0] if size == 1 else unique_segments

        return None


    @staticmethod
    async def find_segment_with_context(
            quote: str, logger: logging.Logger, series_name: str, context_size: int = 30,
            season_filter: Optional[int] = None, episode_filter: Optional[int] = None,
            index: str = None,
    ) -> Optional[json]:
        await log_system_message(
            logging.INFO,
            f"Searching for quote: '{quote}' in series '{series_name}' with context size: {context_size}. Season: {season_filter}, Episode: {episode_filter}",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        if index is None:
            index = f"{series_name}_text_segments"

        segment = await TranscriptionFinder.find_segment_by_quote(quote, logger, series_name, season_filter, episode_filter)
        if not segment:
            await log_system_message(logging.INFO, "No segments found matching the query.", logger)
            return None

        segment = segment[0] if isinstance(segment, list) else segment
        episode_data = segment.get("episode_metadata", segment.get("episode_info", {}))
        segment_id = segment.get("segment_id", segment.get("id"))

        context_segments = await TranscriptionFinder._fetch_context_segments(
            es, index, episode_data, segment_id, context_size,
        )

        segment_start = segment.get("start_time", segment.get("start"))
        segment_end = segment.get("end_time", segment.get("end"))
        unique_context_segments = TranscriptionFinder._build_unique_segments(
            context_segments, segment_id, segment, segment_start, segment_end,
        )

        await log_system_message(logging.INFO, f"Found {len(unique_context_segments)} unique segments for context.", logger)

        overall_start_time = min(seg['start'] for seg in unique_context_segments)
        overall_end_time = max(seg['end'] for seg in unique_context_segments)

        return {
            "target": segment,
            "context": unique_context_segments,
            "overall_start_time": overall_start_time,
            "overall_end_time": overall_end_time,
        }

    @staticmethod
    async def _fetch_context_segments(
            es: ObjectApiResponse, index: str, episode_data: Dict[str, Any], segment_id: int, context_size: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        context_query_before = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"episode_metadata.season": episode_data["season"]}},
                        {"term": {"episode_metadata.episode_number": episode_data["episode_number"]}},
                    ],
                    "filter": [
                        {"range": {"segment_id": {"lt": segment_id}}},
                    ],
                },
            },
            "sort": [{"segment_id": "desc"}],
            "size": context_size,
        }

        context_query_after = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"episode_metadata.season": episode_data["season"]}},
                        {"term": {"episode_metadata.episode_number": episode_data["episode_number"]}},
                    ],
                    "filter": [
                        {"range": {"segment_id": {"gt": segment_id}}},
                    ],
                },
            },
            "sort": [{"segment_id": "asc"}],
            "size": context_size,
        }

        context_response_before = await es.search(index=index, body=context_query_before)
        context_response_after = await es.search(index=index, body=context_query_after)

        context_segments_before = [{
            "id": hit["_source"].get("segment_id", hit["_source"].get("id")),
            "text": hit["_source"]["text"],
            "start": hit["_source"].get("start_time", hit["_source"].get("start")),
            "end": hit["_source"].get("end_time", hit["_source"].get("end")),
        } for hit in context_response_before["hits"]["hits"]]

        context_segments_after = [{
            "id": hit["_source"].get("segment_id", hit["_source"].get("id")),
            "text": hit["_source"]["text"],
            "start": hit["_source"].get("start_time", hit["_source"].get("start")),
            "end": hit["_source"].get("end_time", hit["_source"].get("end")),
        } for hit in context_response_after["hits"]["hits"]]

        context_segments_before.reverse()
        return context_segments_before, context_segments_after

    @staticmethod
    def _build_unique_segments(
            context_segments: Tuple[List[Dict[str, Any]], List[Dict[str, Any]]],
            segment_id: int,
            segment: Dict[str, Any],
            segment_start: float,
            segment_end: float,
    ) -> List[Dict[str, Any]]:
        context_segments_before, context_segments_after = context_segments
        unique_context_segments = []
        for seg in (
            context_segments_before + [{"id": segment_id, "text": segment["text"], "start": segment_start, "end": segment_end}] +
            context_segments_after
        ):
            if seg not in unique_context_segments:
                unique_context_segments.append(seg)
        return unique_context_segments

    @staticmethod
    async def find_video_path_by_episode(
            season: int, episode_number: int, logger: logging.Logger,
            index: str = settings.ES_TRANSCRIPTION_INDEX,
    ) -> Optional[str]:
        await log_system_message(
            logging.INFO,
            f"Searching for video path with filters - Season: {season}, Episode: {episode_number}",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"episode_metadata.season": season}},
                        {"term": {"episode_metadata.episode_number": episode_number}},
                    ],
                },
            },
        }

        response = await es.search(index=index, body=query, size=1)
        hits = response["hits"]["hits"]

        if not hits:
            await log_system_message(logging.INFO, "No segments found matching the query.", logger)
            return None

        segment = hits[0]["_source"]
        video_path = segment.get("video_path", None)

        if video_path:
            await log_system_message(logging.INFO, f"Found video path: {video_path}", logger)
            return video_path

        await log_system_message(logging.INFO, "Video path not found in the segment.", logger)
        return None

    @staticmethod
    async def find_episodes_by_season(season: int, logger: logging.Logger, index: str = settings.ES_TRANSCRIPTION_INDEX) -> Optional[List[json]]:
        await log_system_message(logging.INFO, f"Searching for episodes in season {season}", logger)
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            "size": 0,
            "query": {
                "term": {"episode_metadata.season": season},
            },
            "aggs": {
                "unique_episodes": {
                    "terms": {
                        "field": "episode_metadata.episode_number",
                        "size": 1000,
                        "order": {
                            "_key": "asc",
                        },
                    },
                    "aggs": {
                        "episode_metadata": {
                            "top_hits": {
                                "size": 1,
                                "_source": {
                                    "includes": [
                                        "episode_metadata.title",
                                        "episode_metadata.premiere_date",
                                        "episode_metadata.viewership",
                                        "episode_metadata.episode_number",
                                    ],
                                },
                            },
                        },
                    },
                },
            },
        }

        response = await es.search(index=index, body=query)
        buckets = response["aggregations"]["unique_episodes"]["buckets"]

        if not buckets:
            await log_system_message(logging.INFO, f"No episodes found for season {season}.", logger)
            return None

        episodes = []
        for bucket in buckets:
            episode_metadata = bucket["episode_metadata"]["hits"]["hits"][0]["_source"]["episode_metadata"]
            episode = {
                "episode_number": episode_metadata.get("episode_number"),
                "title": episode_metadata.get("title", "Unknown"),
                "premiere_date": episode_metadata.get("premiere_date", "Unknown"),
                "viewership": episode_metadata.get("viewership", "Unknown"),
            }
            episodes.append(episode)

        await log_system_message(logging.INFO, f"Found {len(episodes)} episodes for season {season}.", logger)
        return episodes

    @staticmethod
    async def get_season_details_from_elastic(
            logger: logging.Logger,
            index: str = settings.ES_TRANSCRIPTION_INDEX,
    ) -> Dict[str, int]:
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        agg_query = {
            "size": 0,
            "aggs": {
                "seasons": {
                    "terms": {
                        "field": "episode_metadata.season",
                        "size": 1000,
                        "order": {"_key": "asc"},
                    },
                    "aggs": {
                        "unique_episodes": {
                            "cardinality": {
                                "field": "episode_metadata.episode_number",
                            },
                        },
                    },
                },
            },
        }

        await log_system_message(logging.INFO, "Fetching season details via Elasticsearch aggregation.", logger)
        response = await es.search(index=index, body=agg_query)
        buckets = response["aggregations"]["seasons"]["buckets"]

        season_dict: Dict[str, int] = {}
        for bucket in buckets:
            season_key = str(bucket["key"])
            episodes_count = bucket["unique_episodes"]["value"]
            season_dict[season_key] = episodes_count

        await log_system_message(logging.INFO, f"Season details: {season_dict}", logger)
        return season_dict
