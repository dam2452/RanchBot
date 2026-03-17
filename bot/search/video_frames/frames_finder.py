import logging
from typing import (
    List,
    Optional,
)

from bot.search.infra.elastic_search_manager import ElasticSearchManager
from bot.settings import settings
from bot.types import VideoFrameSource
from bot.utils.constants import (
    DetectedObjectKeys,
    ElasticsearchAggregationKeys,
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EpisodeMetadataKeys,
    VideoFrameKeys,
)
from bot.utils.log import log_system_message


def _build_index(series_name: str) -> str:
    return f"{series_name}{ElasticsearchIndexSuffixes.VIDEO_FRAMES}"


class VideoFramesFinder:
    @staticmethod
    async def find_frames_in_episode(  # pylint: disable=duplicate-code
        season: int,
        episode_number: int,
        series_name: str,
        logger: logging.Logger,
    ) -> List[VideoFrameSource]:
        await log_system_message(
            logging.INFO,
            f"Fetching frames for S{season:02d}E{episode_number:02d} in '{series_name}'.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST: [
                        {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.SEASON_FIELD: season}},
                        {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: episode_number}},
                    ],
                },
            },
            ElasticsearchQueryKeys.SORT: [{VideoFrameKeys.TIMESTAMP: ElasticsearchQueryKeys.ASC}],
            ElasticsearchQueryKeys.SIZE: settings.MAX_ES_RESULTS_LONG,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        frames = [h[ElasticsearchKeys.SOURCE] for h in hits]
        await log_system_message(
            logging.INFO, f"Found {len(frames)} frames for S{season:02d}E{episode_number:02d}.", logger,
        )
        return frames

    @staticmethod
    async def find_frames_near_timestamp(
        season: int,
        episode_number: int,
        timestamp: float,
        radius_seconds: float,
        series_name: str,
        logger: logging.Logger,
    ) -> List[VideoFrameSource]:
        await log_system_message(
            logging.INFO,
            f"Fetching frames near {timestamp:.2f}s (±{radius_seconds}s) in S{season:02d}E{episode_number:02d}.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST: [
                        {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.SEASON_FIELD: season}},
                        {ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: episode_number}},
                        {
                            ElasticsearchQueryKeys.RANGE: {
                                VideoFrameKeys.TIMESTAMP: {
                                    ElasticsearchQueryKeys.GT: timestamp - radius_seconds,
                                    ElasticsearchQueryKeys.LT: timestamp + radius_seconds,
                                },
                            },
                        },
                    ],
                },
            },
            ElasticsearchQueryKeys.SORT: [{VideoFrameKeys.TIMESTAMP: ElasticsearchQueryKeys.ASC}],
            ElasticsearchQueryKeys.SIZE: 100,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        return [h[ElasticsearchKeys.SOURCE] for h in hits]

    @staticmethod
    async def find_frames_with_detected_object(
        object_class: str,
        series_name: str,
        logger: logging.Logger,
        season_filter: Optional[int] = None,
        episode_filter: Optional[int] = None,
    ) -> List[VideoFrameSource]:
        await log_system_message(
            logging.INFO, f"Fetching frames with object '{object_class}' in '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        must_clauses = [
            {
                ElasticsearchQueryKeys.NESTED: {
                    ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS,
                    ElasticsearchQueryKeys.QUERY: {
                        ElasticsearchQueryKeys.TERM: {DetectedObjectKeys.OBJECT_CLASS_FIELD: object_class},
                    },
                },
            },
        ]
        if season_filter is not None:
            must_clauses.append({ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.SEASON_FIELD: season_filter}})
        if episode_filter is not None:
            must_clauses.append({ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: episode_filter}})

        object_count_field = f"{VideoFrameKeys.DETECTED_OBJECTS}.count"
        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {ElasticsearchQueryKeys.MUST: must_clauses},
            },
            ElasticsearchQueryKeys.SORT: [
                {
                    object_count_field: {
                        ElasticsearchQueryKeys.ORDER: ElasticsearchQueryKeys.DESC,
                        ElasticsearchQueryKeys.NESTED: {
                            ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS,
                            ElasticsearchQueryKeys.FILTER: {
                                ElasticsearchQueryKeys.TERM: {DetectedObjectKeys.OBJECT_CLASS_FIELD: object_class},
                            },
                        },
                        ElasticsearchQueryKeys.MODE: ElasticsearchQueryKeys.MAX,
                    },
                },
            ],
            ElasticsearchQueryKeys.SIZE: settings.MAX_ES_RESULTS_LONG,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        frames = [h[ElasticsearchKeys.SOURCE] for h in hits]
        await log_system_message(
            logging.INFO, f"Found {len(frames)} frames with object '{object_class}'.", logger,
        )
        return frames

    @staticmethod
    async def get_all_detected_objects(  # pylint: disable=duplicate-code
        series_name: str,
        logger: logging.Logger,
    ) -> List[str]:
        await log_system_message(
            logging.INFO, f"Fetching all detected object classes for series '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.AGGS: {
                ElasticsearchAggregationKeys.OBJECTS: {
                    ElasticsearchQueryKeys.NESTED: {ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS},
                    ElasticsearchQueryKeys.AGGS: {
                        ElasticsearchAggregationKeys.CLASSES: {
                            ElasticsearchQueryKeys.TERMS: {
                                ElasticsearchQueryKeys.FIELD: DetectedObjectKeys.OBJECT_CLASS_FIELD,
                                ElasticsearchQueryKeys.SIZE: 500,
                                ElasticsearchQueryKeys.ORDER: {ElasticsearchQueryKeys.KEY: ElasticsearchQueryKeys.ASC},
                            },
                        },
                    },
                },
            },
        }

        response = await es.search(index=_build_index(series_name), body=query)
        buckets = (
            response[ElasticsearchKeys.AGGREGATIONS]
            [ElasticsearchAggregationKeys.OBJECTS]
            [ElasticsearchAggregationKeys.CLASSES]
            [ElasticsearchKeys.BUCKETS]
        )
        classes = [b[ElasticsearchKeys.KEY] for b in buckets]
        await log_system_message(logging.INFO, f"Found {len(classes)} detected object classes.", logger)
        return classes
