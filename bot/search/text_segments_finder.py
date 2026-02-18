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
from bot.types import (
    BaseSegment,
    ElasticsearchSegment,
    EpisodeInfo,
    SeasonInfoDict,
    SegmentWithScore,
    TranscriptionContext,
)
from bot.utils.constants import (
    ElasticsearchAggregationKeys,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EpisodeMetadataKeys,
    SegmentKeys,
    TranscriptionContextKeys,
)
from bot.utils.log import log_system_message


class TextSegmentsFinder:
    @staticmethod
    def is_segment_overlap(
            previous_segment: ElasticsearchSegment,
            segment: ElasticsearchSegment,
            start_time: float,
    ) -> bool:
        if not previous_segment:
            return False

        prev_metadata = previous_segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
        curr_metadata = segment[EpisodeMetadataKeys.EPISODE_METADATA]

        prev_season = prev_metadata.get(EpisodeMetadataKeys.SEASON)
        curr_season = curr_metadata[EpisodeMetadataKeys.SEASON]

        prev_episode = prev_metadata.get(EpisodeMetadataKeys.EPISODE_NUMBER)
        curr_episode = curr_metadata[EpisodeMetadataKeys.EPISODE_NUMBER]

        prev_end_time = previous_segment.get(
            SegmentKeys.END_TIME,
            previous_segment.get(SegmentKeys.END, 0),
        )

        return (
            prev_season == curr_season and
            prev_episode == curr_episode and
            start_time <= prev_end_time
        )

    @staticmethod
    async def find_segment_by_quote(
            quote: str, logger: logging.Logger, series_name: str, season_filter: Optional[int] = None,
            episode_filter: Optional[int] = None,
            size: int = 1,
    ) -> Optional[Union[SegmentWithScore, List[SegmentWithScore]]]:
        def __merge_overlapping_segment(
            incoming: SegmentWithScore,
            collected: List[SegmentWithScore],
            incoming_start: float,
            incoming_end: float,
        ) -> bool:
            for i, existing_segment in enumerate(collected):
                existing_start = existing_segment[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE
                existing_end = existing_segment[SegmentKeys.END_TIME] + settings.EXTEND_AFTER

                seg_metadata = incoming.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
                existing_metadata = existing_segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {})

                seg_season = seg_metadata.get(EpisodeMetadataKeys.SEASON)
                existing_season = existing_metadata.get(EpisodeMetadataKeys.SEASON)

                seg_episode = seg_metadata.get(EpisodeMetadataKeys.EPISODE_NUMBER)
                existing_episode = existing_metadata.get(EpisodeMetadataKeys.EPISODE_NUMBER)

                if (
                    seg_season == existing_season and
                    seg_episode == existing_episode and
                    incoming_start <= existing_end and
                    incoming_end >= existing_start
                ):
                    collected[i][SegmentKeys.START_TIME] = min(
                        existing_segment[SegmentKeys.START_TIME],
                        incoming[SegmentKeys.START_TIME],
                    )
                    collected[i][SegmentKeys.END_TIME] = max(
                        existing_segment[SegmentKeys.END_TIME],
                        incoming[SegmentKeys.END_TIME],
                    )
                    collected[i][ElasticsearchKeys.SCORE] = max(
                        existing_segment[ElasticsearchKeys.SCORE],
                        incoming[ElasticsearchKeys.SCORE],
                    )
                    return True
            return False

        await log_system_message(
            logging.INFO,
            f"Searching for quote: '{quote}' in series '{series_name}' with filters - Season: {season_filter}, Episode: {episode_filter}",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        index = f"{series_name}_text_segments"

        query: Dict[str, Any] = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST: {
                        ElasticsearchQueryKeys.MATCH: {
                            SegmentKeys.TEXT: {
                                ElasticsearchQueryKeys.QUERY: quote,
                                ElasticsearchQueryKeys.FUZZINESS: ElasticsearchQueryKeys.AUTO,
                            },
                        },
                    },
                    ElasticsearchQueryKeys.FILTER: [
                        {ElasticsearchQueryKeys.TERM: {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SERIES_NAME}": series_name}},
                    ],
                },
            },
            ElasticsearchQueryKeys.SORT: [
                {ElasticsearchKeys.SCORE: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.DESC}},
                {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
                {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}": {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
                {SegmentKeys.START_TIME: {ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.ASC}},
            ],
        }

        if season_filter:
            query[ElasticsearchQueryKeys.QUERY][ElasticsearchQueryKeys.BOOL][ElasticsearchQueryKeys.FILTER].append(
                {ElasticsearchQueryKeys.TERM: {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": season_filter}},
            )

        if episode_filter:
            query[ElasticsearchQueryKeys.QUERY][ElasticsearchQueryKeys.BOOL][ElasticsearchQueryKeys.FILTER].append(
                {ElasticsearchQueryKeys.TERM: {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}": episode_filter}},
            )

        hits = (await es.search(index=index, body=query, size=size))[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]

        if not hits:
            await log_system_message(logging.INFO, "No segments found matching the query.", logger)
            return None

        unique_segments = []
        seen_segments = set()

        for hit in hits:
            segment = hit[ElasticsearchKeys.SOURCE]
            segment[ElasticsearchKeys.SCORE] = hit[ElasticsearchKeys.SCORE]
            segment_key = (
                segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.SEASON),
                segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.EPISODE_NUMBER),
                segment.get(SegmentKeys.START_TIME),
                segment.get(SegmentKeys.END_TIME),
            )

            if segment_key not in seen_segments:
                seen_segments.add(segment_key)

                start_time = segment[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE
                end_time = segment[SegmentKeys.END_TIME] + settings.EXTEND_AFTER

                is_overlapping = __merge_overlapping_segment(segment, unique_segments, start_time, end_time)

                if not is_overlapping:
                    unique_segments.append(segment)

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
            index: Optional[str] = None,
    ) -> Optional[TranscriptionContext]:
        await log_system_message(
            logging.INFO,
            f"Searching for quote: '{quote}' in series '{series_name}' with context size: {context_size}. Season: {season_filter}, Episode: {episode_filter}",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        if index is None:
            index = f"{series_name}_text_segments"

        segment = await TextSegmentsFinder.find_segment_by_quote(quote, logger, series_name, season_filter, episode_filter)
        if not segment:
            await log_system_message(logging.INFO, "No segments found matching the query.", logger)
            return None

        segment = segment[0] if isinstance(segment, list) else segment
        episode_data = segment.get(
            EpisodeMetadataKeys.EPISODE_METADATA,
            segment.get(EpisodeMetadataKeys.EPISODE_INFO, {}),
        )
        segment_id = segment.get(SegmentKeys.SEGMENT_ID, segment.get(SegmentKeys.ID))

        context_segments = await TextSegmentsFinder._fetch_context_segments(
            es, index, episode_data, segment_id, context_size,
        )

        segment_start = segment.get(SegmentKeys.START_TIME, segment.get(SegmentKeys.START))
        segment_end = segment.get(SegmentKeys.END_TIME, segment.get(SegmentKeys.END))
        unique_context_segments = TextSegmentsFinder.__build_unique_segments(
            context_segments, segment_id, segment, segment_start, segment_end,
        )

        await log_system_message(logging.INFO, f"Found {len(unique_context_segments)} unique segments for context.", logger)

        overall_start_time = min(seg[SegmentKeys.START] for seg in unique_context_segments)
        overall_end_time = max(seg[SegmentKeys.END] for seg in unique_context_segments)

        result: TranscriptionContext = {
            TranscriptionContextKeys.TARGET: segment,
            TranscriptionContextKeys.CONTEXT: unique_context_segments,
            TranscriptionContextKeys.OVERALL_START_TIME: overall_start_time,
            TranscriptionContextKeys.OVERALL_END_TIME: overall_end_time,
        }
        return result

    @staticmethod
    async def _fetch_context_segments(
            es: ObjectApiResponse,
            index: str,
            episode_data: ElasticsearchSegment,
            segment_id: int,
            context_size: int,
    ) -> Tuple[List[BaseSegment], List[BaseSegment]]:
        season_field = f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}"
        episode_field = (
            f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}"
        )

        context_query_before: Dict[str, Any] = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST: [
                        {ElasticsearchQueryKeys.TERM: {season_field: episode_data[EpisodeMetadataKeys.SEASON]}},
                        {
                            ElasticsearchQueryKeys.TERM: {
                                episode_field: episode_data[EpisodeMetadataKeys.EPISODE_NUMBER],
                            },
                        },
                    ],
                    ElasticsearchQueryKeys.FILTER: [
                        {ElasticsearchQueryKeys.RANGE: {SegmentKeys.SEGMENT_ID: {ElasticsearchQueryKeys.LT: segment_id}}},
                    ],
                },
            },
            ElasticsearchQueryKeys.SORT: [{SegmentKeys.SEGMENT_ID: ElasticsearchQueryKeys.DESC}],
            ElasticsearchQueryKeys.SIZE: context_size,
        }

        context_query_after: Dict[str, Any] = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST: [
                        {ElasticsearchQueryKeys.TERM: {season_field: episode_data[EpisodeMetadataKeys.SEASON]}},
                        {
                            ElasticsearchQueryKeys.TERM: {
                                episode_field: episode_data[EpisodeMetadataKeys.EPISODE_NUMBER],
                            },
                        },
                    ],
                    ElasticsearchQueryKeys.FILTER: [
                        {ElasticsearchQueryKeys.RANGE: {SegmentKeys.SEGMENT_ID: {ElasticsearchQueryKeys.GT: segment_id}}},
                    ],
                },
            },
            ElasticsearchQueryKeys.SORT: [{SegmentKeys.SEGMENT_ID: ElasticsearchQueryKeys.ASC}],
            ElasticsearchQueryKeys.SIZE: context_size,
        }

        context_response_before = await es.search(index=index, body=context_query_before)
        context_response_after = await es.search(index=index, body=context_query_after)

        context_segments_before: List[BaseSegment] = [{
            SegmentKeys.ID: hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.SEGMENT_ID, hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.ID)),
            SegmentKeys.TEXT: hit[ElasticsearchKeys.SOURCE][SegmentKeys.TEXT],
            SegmentKeys.START: hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.START_TIME, hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.START)),
            SegmentKeys.END: hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.END_TIME, hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.END)),
        } for hit in context_response_before[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]]

        context_segments_after: List[BaseSegment] = [{
            SegmentKeys.ID: hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.SEGMENT_ID, hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.ID)),
            SegmentKeys.TEXT: hit[ElasticsearchKeys.SOURCE][SegmentKeys.TEXT],
            SegmentKeys.START: hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.START_TIME, hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.START)),
            SegmentKeys.END: hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.END_TIME, hit[ElasticsearchKeys.SOURCE].get(SegmentKeys.END)),
        } for hit in context_response_after[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]]

        context_segments_before.reverse()
        return context_segments_before, context_segments_after

    @staticmethod
    def __build_unique_segments(
            context_segments: Tuple[List[BaseSegment], List[BaseSegment]],
            segment_id: int,
            segment: ElasticsearchSegment,
            segment_start: float,
            segment_end: float,
    ) -> List[BaseSegment]:
        context_segments_before, context_segments_after = context_segments
        unique_context_segments = []

        target_segment = {
            SegmentKeys.ID: segment_id,
            SegmentKeys.TEXT: segment[SegmentKeys.TEXT],
            SegmentKeys.START: segment_start,
            SegmentKeys.END: segment_end,
        }

        all_segments = context_segments_before + [target_segment] + context_segments_after

        for seg in all_segments:
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

        query: Dict[str, Any] = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST: [
                        {ElasticsearchQueryKeys.TERM: {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": season}},
                        {ElasticsearchQueryKeys.TERM: {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}": episode_number}},
                    ],
                },
            },
        }

        response = await es.search(index=index, body=query, size=1)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]

        if not hits:
            await log_system_message(logging.INFO, "No segments found matching the query.", logger)
            return None

        segment = hits[0][ElasticsearchKeys.SOURCE]
        video_path = segment.get(SegmentKeys.VIDEO_PATH, None)

        if video_path:
            await log_system_message(logging.INFO, f"Found video path: {video_path}", logger)
            return video_path

        await log_system_message(logging.INFO, "Video path not found in the segment.", logger)
        return None

    @staticmethod
    async def find_episodes_by_season(season: int, logger: logging.Logger, index: str = settings.ES_TRANSCRIPTION_INDEX) -> Optional[List[EpisodeInfo]]:
        await log_system_message(logging.INFO, f"Searching for episodes in season {season}", logger)
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query: Dict[str, Any] = {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.TERM: {f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": season},
            },
            ElasticsearchQueryKeys.AGGS: {
                ElasticsearchAggregationKeys.UNIQUE_EPISODES: {
                    ElasticsearchQueryKeys.TERMS: {
                        ElasticsearchQueryKeys.FIELD: f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}",
                        ElasticsearchQueryKeys.SIZE: 1000,
                        ElasticsearchQueryKeys.ORDER: {
                            ElasticsearchQueryKeys.KEY: ElasticsearchQueryKeys.ASC,
                        },
                    },
                    ElasticsearchQueryKeys.AGGS: {
                        EpisodeMetadataKeys.EPISODE_METADATA: {
                            ElasticsearchQueryKeys.TOP_HITS: {
                                ElasticsearchQueryKeys.SIZE: 1,
                                ElasticsearchQueryKeys.SOURCE: {
                                    ElasticsearchQueryKeys.INCLUDES: [
                                        f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.TITLE}",
                                        f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.PREMIERE_DATE}",
                                        f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.VIEWERSHIP}",
                                        f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}",
                                    ],
                                },
                            },
                        },
                    },
                },
            },
        }

        response = await es.search(index=index, body=query)
        buckets = response[ElasticsearchKeys.AGGREGATIONS][ElasticsearchAggregationKeys.UNIQUE_EPISODES][ElasticsearchKeys.BUCKETS]

        if not buckets:
            await log_system_message(logging.INFO, f"No episodes found for season {season}.", logger)
            return None

        episodes = []
        for bucket in buckets:
            hits_data = bucket[EpisodeMetadataKeys.EPISODE_METADATA][ElasticsearchKeys.HITS]
            source_data = hits_data[ElasticsearchKeys.HITS][0][ElasticsearchKeys.SOURCE]
            episode_metadata = source_data[EpisodeMetadataKeys.EPISODE_METADATA]

            episode = {
                EpisodeMetadataKeys.EPISODE_NUMBER: episode_metadata.get(
                    EpisodeMetadataKeys.EPISODE_NUMBER,
                ),
                EpisodeMetadataKeys.TITLE: episode_metadata.get(EpisodeMetadataKeys.TITLE, "Unknown"),
                EpisodeMetadataKeys.PREMIERE_DATE: episode_metadata.get(EpisodeMetadataKeys.PREMIERE_DATE, "Unknown"),
                EpisodeMetadataKeys.VIEWERSHIP: episode_metadata.get(EpisodeMetadataKeys.VIEWERSHIP, "Unknown"),
            }
            episodes.append(episode)

        await log_system_message(logging.INFO, f"Found {len(episodes)} episodes for season {season}.", logger)
        return episodes

    @staticmethod
    async def get_season_details_from_elastic(
            logger: logging.Logger,
            series_name: str,
    ) -> SeasonInfoDict:
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)
        index = f"{series_name}_text_segments"

        agg_query: Dict[str, Any] = {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.AGGS: {
                ElasticsearchAggregationKeys.SEASONS: {
                    ElasticsearchQueryKeys.TERMS: {
                        ElasticsearchQueryKeys.FIELD: f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}",
                        ElasticsearchQueryKeys.SIZE: 1000,
                        ElasticsearchQueryKeys.ORDER: {ElasticsearchQueryKeys.KEY: ElasticsearchQueryKeys.ASC},
                    },
                    ElasticsearchQueryKeys.AGGS: {
                        ElasticsearchAggregationKeys.UNIQUE_EPISODES: {
                            ElasticsearchQueryKeys.CARDINALITY: {
                                ElasticsearchQueryKeys.FIELD: f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}",
                            },
                        },
                    },
                },
            },
        }

        await log_system_message(logging.INFO, "Fetching season details via Elasticsearch aggregation.", logger)
        response = await es.search(index=index, body=agg_query)
        buckets = response[ElasticsearchKeys.AGGREGATIONS][ElasticsearchAggregationKeys.SEASONS][ElasticsearchKeys.BUCKETS]

        season_dict: SeasonInfoDict = {}
        for bucket in buckets:
            season_key = str(bucket[ElasticsearchKeys.KEY])
            episodes_count = bucket[ElasticsearchAggregationKeys.UNIQUE_EPISODES][ElasticsearchAggregationKeys.VALUE]
            season_dict[season_key] = episodes_count

        await log_system_message(logging.INFO, f"Season details: {season_dict}", logger)
        return season_dict
