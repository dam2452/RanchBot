import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.search.elastic_search_manager import (
    ElasticSearchManager,
    build_bool_must_query,
    extract_sources,
)
from bot.utils.constants import (
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EpisodeMetadataKeys,
    VideoFrameKeys,
)
from bot.utils.log import log_system_message

_SEASON_FIELD = f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}"
_EPISODE_FIELD = f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}"
_OBJECT_CLASS_FIELD = f"{VideoFrameKeys.DETECTED_OBJECTS}.class"


def _build_index(series_name: str) -> str:
    return f"{series_name}{ElasticsearchIndexSuffixes.VIDEO_FRAMES}"


class VideoFramesFinder:
    @staticmethod
    async def find_frames_in_episode(
        season: int,
        episode_number: int,
        series_name: str,
        logger: logging.Logger,
    ) -> List[Dict[str, Any]]:
        await log_system_message(
            logging.INFO,
            f"Fetching frames for S{season:02d}E{episode_number:02d} in '{series_name}'.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            **build_bool_must_query([
                {ElasticsearchQueryKeys.TERM: {_SEASON_FIELD: season}},
                {ElasticsearchQueryKeys.TERM: {_EPISODE_FIELD: episode_number}},
            ]),
            ElasticsearchQueryKeys.SORT: [{VideoFrameKeys.TIMESTAMP: ElasticsearchQueryKeys.ASC}],
            ElasticsearchQueryKeys.SIZE: 9999,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        frames = extract_sources(response)
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
    ) -> List[Dict[str, Any]]:
        await log_system_message(
            logging.INFO,
            f"Fetching frames near {timestamp:.2f}s (±{radius_seconds}s) in S{season:02d}E{episode_number:02d}.",
            logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            **build_bool_must_query([
                {ElasticsearchQueryKeys.TERM: {_SEASON_FIELD: season}},
                {ElasticsearchQueryKeys.TERM: {_EPISODE_FIELD: episode_number}},
                {
                    ElasticsearchQueryKeys.RANGE: {
                        VideoFrameKeys.TIMESTAMP: {
                            ElasticsearchQueryKeys.GT: timestamp - radius_seconds,
                            ElasticsearchQueryKeys.LT: timestamp + radius_seconds,
                        },
                    },
                },
            ]),
            ElasticsearchQueryKeys.SORT: [{VideoFrameKeys.TIMESTAMP: ElasticsearchQueryKeys.ASC}],
            ElasticsearchQueryKeys.SIZE: 100,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        return extract_sources(response)

    @staticmethod
    async def find_frames_with_detected_object(
        object_class: str,
        series_name: str,
        logger: logging.Logger,
        season_filter: Optional[int] = None,
        episode_filter: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        await log_system_message(
            logging.INFO, f"Fetching frames with object '{object_class}' in '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        must_clauses: List[Dict[str, Any]] = [
            {
                ElasticsearchQueryKeys.NESTED: {
                    ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS,
                    ElasticsearchQueryKeys.QUERY: {
                        ElasticsearchQueryKeys.TERM: {_OBJECT_CLASS_FIELD: object_class},
                    },
                },
            },
        ]
        if season_filter is not None:
            must_clauses.append({ElasticsearchQueryKeys.TERM: {_SEASON_FIELD: season_filter}})
        if episode_filter is not None:
            must_clauses.append({ElasticsearchQueryKeys.TERM: {_EPISODE_FIELD: episode_filter}})

        query = {
            **build_bool_must_query(must_clauses),
            ElasticsearchQueryKeys.SORT: [
                {_SEASON_FIELD: ElasticsearchQueryKeys.ASC},
                {_EPISODE_FIELD: ElasticsearchQueryKeys.ASC},
                {VideoFrameKeys.TIMESTAMP: ElasticsearchQueryKeys.ASC},
            ],
            ElasticsearchQueryKeys.SIZE: 999,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        frames = extract_sources(response)
        await log_system_message(
            logging.INFO, f"Found {len(frames)} frames with object '{object_class}'.", logger,
        )
        return frames

    @staticmethod
    async def get_all_detected_objects(
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
                "objects": {
                    ElasticsearchQueryKeys.NESTED: {ElasticsearchQueryKeys.PATH: VideoFrameKeys.DETECTED_OBJECTS},
                    ElasticsearchQueryKeys.AGGS: {
                        "classes": {
                            ElasticsearchQueryKeys.TERMS: {
                                ElasticsearchQueryKeys.FIELD: _OBJECT_CLASS_FIELD,
                                ElasticsearchQueryKeys.SIZE: 500,
                                ElasticsearchQueryKeys.ORDER: {ElasticsearchQueryKeys.KEY: ElasticsearchQueryKeys.ASC},
                            },
                        },
                    },
                },
            },
        }

        response = await es.search(index=_build_index(series_name), body=query)
        buckets = response[ElasticsearchKeys.AGGREGATIONS]["objects"]["classes"][ElasticsearchKeys.BUCKETS]
        classes = [b[ElasticsearchKeys.KEY] for b in buckets]
        await log_system_message(logging.INFO, f"Found {len(classes)} detected object classes.", logger)
        return classes
