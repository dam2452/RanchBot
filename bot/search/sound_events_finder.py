import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.search.infra.elastic_search_manager import ElasticSearchManager
from bot.settings import settings
from bot.utils.constants import (
    ElasticsearchAggregationKeys,
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EpisodeMetadataKeys,
    SegmentKeys,
    SoundEventKeys,
)
from bot.utils.log import log_system_message


def _build_index(series_name: str) -> str:
    return f"{series_name}{ElasticsearchIndexSuffixes.SOUND_EVENTS}"


class SoundEventsFinder:
    __SOUND_SEGMENT_SOURCE_FIELDS = [
        EpisodeMetadataKeys.EPISODE_METADATA,
        SegmentKeys.SEGMENT_ID,
        SegmentKeys.TEXT,
        SegmentKeys.START_TIME,
        SegmentKeys.END_TIME,
        SegmentKeys.VIDEO_PATH,
        SoundEventKeys.SOUND_TYPE,
    ]

    @staticmethod
    async def get_all_sound_types(
        series_name: str,
        logger: logging.Logger,
    ) -> List[str]:
        await log_system_message(
            logging.INFO, f"Fetching all sound types for series '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.AGGS: {
                ElasticsearchAggregationKeys.SOUND_TYPES: {
                    ElasticsearchQueryKeys.TERMS: {
                        ElasticsearchQueryKeys.FIELD: SoundEventKeys.SOUND_TYPE,
                        ElasticsearchQueryKeys.SIZE: 100,
                        ElasticsearchQueryKeys.ORDER: {ElasticsearchQueryKeys.KEY: ElasticsearchQueryKeys.ASC},
                    },
                },
            },
        }

        response = await es.search(index=_build_index(series_name), body=query)
        buckets = response[ElasticsearchKeys.AGGREGATIONS][ElasticsearchAggregationKeys.SOUND_TYPES][ElasticsearchKeys.BUCKETS]
        sound_types = [b[ElasticsearchKeys.KEY] for b in buckets]
        await log_system_message(logging.INFO, f"Found {len(sound_types)} sound types.", logger)
        return sound_types

    @staticmethod
    async def find_segments_by_sound_type(
        sound_type: str,
        series_name: str,
        logger: logging.Logger,
        season_filter: Optional[int] = None,
        episode_filter: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        await log_system_message(
            logging.INFO, f"Fetching '{sound_type}' segments for series '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        filter_clauses: List[Dict[str, Any]] = [
            {ElasticsearchQueryKeys.TERM: {SoundEventKeys.SOUND_TYPE: sound_type}},
        ]
        if season_filter is not None:
            filter_clauses.append({ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.SEASON_FIELD: season_filter}})
        if episode_filter is not None:
            filter_clauses.append({ElasticsearchQueryKeys.TERM: {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: episode_filter}})

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {ElasticsearchQueryKeys.FILTER: filter_clauses},
            },
            ElasticsearchQueryKeys.SORT: [
                {EpisodeMetadataKeys.SEASON_FIELD: ElasticsearchQueryKeys.ASC},
                {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: ElasticsearchQueryKeys.ASC},
                {SegmentKeys.START_TIME: ElasticsearchQueryKeys.ASC},
            ],
            ElasticsearchQueryKeys.SIZE: settings.MAX_ES_RESULTS_LONG,
            ElasticsearchQueryKeys.SOURCE: SoundEventsFinder.__SOUND_SEGMENT_SOURCE_FIELDS,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        segments = [h[ElasticsearchKeys.SOURCE] for h in hits]
        await log_system_message(
            logging.INFO, f"Found {len(segments)} '{sound_type}' segments.", logger,
        )
        return segments

    @staticmethod
    async def search_by_text(
        text_query: str,
        series_name: str,
        logger: logging.Logger,
        size: int = settings.MAX_ES_RESULTS_LONG,
    ) -> List[Dict[str, Any]]:
        await log_system_message(
            logging.INFO, f"Searching sound events for '{text_query}' in '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.MATCH: {
                    SoundEventKeys.TEXT: {
                        ElasticsearchQueryKeys.QUERY: text_query,
                        ElasticsearchQueryKeys.FUZZINESS: ElasticsearchQueryKeys.AUTO,
                    },
                },
            },
            ElasticsearchQueryKeys.SORT: [
                {ElasticsearchKeys.SCORE: ElasticsearchQueryKeys.DESC},
                {EpisodeMetadataKeys.SEASON_FIELD: ElasticsearchQueryKeys.ASC},
                {EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: ElasticsearchQueryKeys.ASC},
                {SegmentKeys.START_TIME: ElasticsearchQueryKeys.ASC},
            ],
            ElasticsearchQueryKeys.SIZE: size,
            ElasticsearchQueryKeys.SOURCE: SoundEventsFinder.__SOUND_SEGMENT_SOURCE_FIELDS,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        segments = [h[ElasticsearchKeys.SOURCE] for h in hits]
        await log_system_message(
            logging.INFO, f"Found {len(segments)} sound segments matching '{text_query}'.", logger,
        )
        return segments
