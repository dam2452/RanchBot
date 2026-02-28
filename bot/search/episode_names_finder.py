import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.search.elastic_search_manager import ElasticSearchManager
from bot.utils.constants import (
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EpisodeMetadataKeys,
)
from bot.utils.log import log_system_message

_SEASON_FIELD = f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}"
_EPISODE_FIELD = f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}"


def _build_index(series_name: str) -> str:
    return f"{series_name}{ElasticsearchIndexSuffixes.EPISODE_NAMES}"


class EpisodeNamesFinder:
    @staticmethod
    async def search_by_title(
        title_query: str,
        series_name: str,
        logger: logging.Logger,
        size: int = 10,
    ) -> List[Dict[str, Any]]:
        await log_system_message(
            logging.INFO, f"Searching episode by title '{title_query}' in '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query: Dict[str, Any] = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.MATCH: {
                    EpisodeMetadataKeys.TITLE: {
                        ElasticsearchQueryKeys.QUERY: title_query,
                        ElasticsearchQueryKeys.FUZZINESS: ElasticsearchQueryKeys.AUTO,
                    },
                },
            },
            ElasticsearchQueryKeys.SORT: [
                {ElasticsearchKeys.SCORE: ElasticsearchQueryKeys.DESC},
                {_SEASON_FIELD: ElasticsearchQueryKeys.ASC},
                {_EPISODE_FIELD: ElasticsearchQueryKeys.ASC},
            ],
            ElasticsearchQueryKeys.SIZE: size,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        episodes = [h[ElasticsearchKeys.SOURCE] for h in hits]
        await log_system_message(
            logging.INFO, f"Found {len(episodes)} episodes matching '{title_query}'.", logger,
        )
        return episodes

    @staticmethod
    async def get_all_episodes(
        series_name: str,
        logger: logging.Logger,
        exclude_season_0: bool = False,
    ) -> List[Dict[str, Any]]:
        await log_system_message(
            logging.INFO, f"Fetching all episodes for series '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query: Dict[str, Any] = {
            ElasticsearchQueryKeys.QUERY: {ElasticsearchQueryKeys.BOOL: {}},
            ElasticsearchQueryKeys.SORT: [
                {_SEASON_FIELD: ElasticsearchQueryKeys.ASC},
                {_EPISODE_FIELD: ElasticsearchQueryKeys.ASC},
            ],
            ElasticsearchQueryKeys.SIZE: 9999,
        }

        if exclude_season_0:
            query[ElasticsearchQueryKeys.QUERY][ElasticsearchQueryKeys.BOOL] = {
                ElasticsearchQueryKeys.MUST_NOT: [
                    {ElasticsearchQueryKeys.TERM: {_SEASON_FIELD: 0}},
                ],
            }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        episodes = [h[ElasticsearchKeys.SOURCE] for h in hits]
        await log_system_message(logging.INFO, f"Found {len(episodes)} episodes.", logger)
        return episodes

    @staticmethod
    async def find_episode_by_exact_id(
        episode_id: str,
        series_name: str,
        logger: logging.Logger,
    ) -> Optional[Dict[str, Any]]:
        await log_system_message(
            logging.INFO, f"Fetching episode '{episode_id}' from '{series_name}'.", logger,
        )
        es = await ElasticSearchManager.connect_to_elasticsearch(logger)

        query: Dict[str, Any] = {
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.TERM: {"episode_id": episode_id},
            },
            ElasticsearchQueryKeys.SIZE: 1,
        }

        response = await es.search(index=_build_index(series_name), body=query)
        hits = response[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
        return hits[0][ElasticsearchKeys.SOURCE] if hits else None
