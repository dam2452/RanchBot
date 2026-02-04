import json
import logging
from typing import (
    Dict,
    List,
    Optional,
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
        previous_segment = {}

        for hit in hits:
            segment = hit["_source"]
            start_time = segment["start_time"] - settings.EXTEND_BEFORE
            end_time = segment["end_time"] + settings.EXTEND_AFTER

            if TranscriptionFinder.is_segment_overlap(previous_segment, segment, start_time):
                previous_segment["end_time"] = max(previous_segment.get("end_time", 0), end_time)
            else:
                unique_segments.append(segment)
                previous_segment = segment

        await log_system_message(
            logging.INFO, f"Found {len(unique_segments)} unique segments after merging.",
            logger,
        )

        if unique_segments:
            return unique_segments[0] if size == 1 else unique_segments

        return None


    @staticmethod
    async def find_segment_with_context(
            quote: str, logger: logging.Logger, context_size: int = 30, season_filter: Optional[str] = None,
            episode_filter: Optional[str] = None,
            index: str = settings.ES_TRANSCRIPTION_INDEX,
    ) -> Optional[json]:
        await log_system_message(
            logging.INFO,
            f"Searching for quote: '{quote}' with context size: {context_size}. Season: {season_filter}, Episode: {episode_filter}",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        segment = await TranscriptionFinder.find_segment_by_quote(quote, logger, season_filter, episode_filter, index)
        if not segment:
            await log_system_message(logging.INFO, "No segments found matching the query.", logger)
            return None

        segment = segment[0] if isinstance(segment, list) else segment

        context_query_before = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"episode_info.season": segment["episode_info"]["season"]}},
                        {"term": {"episode_info.episode_number": segment["episode_info"]["episode_number"]}},
                    ],
                    "filter": [
                        {"range": {"id": {"lt": segment["id"]}}},
                    ],
                },
            },
            "sort": [{"id": "desc"}],
            "size": context_size,
        }

        context_query_after = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"episode_info.season": segment["episode_info"]["season"]}},
                        {"term": {"episode_info.episode_number": segment["episode_info"]["episode_number"]}},
                    ],
                    "filter": [
                        {"range": {"id": {"gt": segment["id"]}}},
                    ],
                },
            },
            "sort": [{"id": "asc"}],
            "size": context_size,
        }

        context_response_before = await es.search(index=index, body=context_query_before)
        context_response_after = await es.search(index=index, body=context_query_after)

        context_segments_before = [{
            "id": hit["_source"]["id"], "text": hit["_source"]["text"], "start": hit["_source"]["start"],
            "end": hit["_source"]["end"],
        } for hit in
                                   context_response_before["hits"]["hits"]]
        context_segments_after = [{
            "id": hit["_source"]["id"], "text": hit["_source"]["text"], "start": hit["_source"]["start"],
            "end": hit["_source"]["end"],
        } for hit in
                                  context_response_after["hits"]["hits"]]

        context_segments_before.reverse()

        unique_context_segments = []
        for seg in (
            context_segments_before + [{"id": segment["id"], "text": segment["text"], "start": segment["start"], "end": segment["end"]}] +
            context_segments_after
        ):
            if seg not in unique_context_segments:
                unique_context_segments.append(seg)

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
                        {"term": {"episode_info.season": season}},
                        {"term": {"episode_info.episode_number": episode_number}},
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
                "term": {"episode_info.season": season},
            },
            "aggs": {
                "unique_episodes": {
                    "terms": {
                        "field": "episode_info.episode_number",
                        "size": 1000,
                        "order": {
                            "_key": "asc",
                        },
                    },
                    "aggs": {
                        "episode_info": {
                            "top_hits": {
                                "size": 1,
                                "_source": {
                                    "includes": [
                                        "episode_info.title",
                                        "episode_info.premiere_date",
                                        "episode_info.viewership",
                                        "episode_info.episode_number",
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
            episode_info = bucket["episode_info"]["hits"]["hits"][0]["_source"]["episode_info"]
            episode = {
                "episode_number": episode_info.get("episode_number"),
                "title": episode_info.get("title", "Unknown"),
                "premiere_date": episode_info.get("premiere_date", "Unknown"),
                "viewership": episode_info.get("viewership", "Unknown"),
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
                        "field": "episode_info.season",
                        "size": 1000,
                        "order": {"_key": "asc"},
                    },
                    "aggs": {
                        "unique_episodes": {
                            "cardinality": {
                                "field": "episode_info.episode_number",
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
