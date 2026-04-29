import logging
from typing import (
    Any,
    Dict,
    List,
)

from bot.search.infra.elastic_search_manager import ElasticSearchManager
from bot.utils.constants import (
    ElasticsearchAggregationKeys,
    ElasticsearchIndexSuffixes,
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EpisodeMetadataKeys,
    SceneInfoKeys,
    VideoFrameKeys,
)
from bot.utils.log import log_system_message


class SceneFinder:
    __SCENE_INFO_FIELD = VideoFrameKeys.SCENE_INFO
    __SCENE_NUMBER_FIELD = f"{VideoFrameKeys.SCENE_INFO}.{SceneInfoKeys.SCENE_NUMBER}"
    __SCENE_START_TIME = f"{VideoFrameKeys.SCENE_INFO}.{SceneInfoKeys.SCENE_START_TIME}"
    __SCENE_END_TIME = f"{VideoFrameKeys.SCENE_INFO}.{SceneInfoKeys.SCENE_END_TIME}"
    __UNIQUE_SCENES_AGG = ElasticsearchAggregationKeys.UNIQUE_SCENES
    __SCENE_START_AGG = ElasticsearchAggregationKeys.SCENE_START
    __SCENE_END_AGG = ElasticsearchAggregationKeys.SCENE_END

    @staticmethod
    def __build_scene_cuts_query(season: int, episode_number: int) -> Dict[str, Any]:
        return {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.FILTER: [
                        {
                            ElasticsearchQueryKeys.TERM: {
                                EpisodeMetadataKeys.SEASON_FIELD: season,
                            },
                        },
                        {
                            ElasticsearchQueryKeys.TERM: {
                                EpisodeMetadataKeys.EPISODE_NUMBER_FIELD: episode_number,
                            },
                        },
                        {
                            ElasticsearchQueryKeys.EXISTS: {
                                ElasticsearchQueryKeys.FIELD: SceneFinder.__SCENE_INFO_FIELD,
                            },
                        },
                    ],
                },
            },
            ElasticsearchQueryKeys.AGGS: {
                SceneFinder.__UNIQUE_SCENES_AGG: {
                    ElasticsearchQueryKeys.TERMS: {
                        ElasticsearchQueryKeys.FIELD: SceneFinder.__SCENE_NUMBER_FIELD,
                        ElasticsearchQueryKeys.SIZE: 2000,
                    },
                    ElasticsearchQueryKeys.AGGS: {
                        SceneFinder.__SCENE_START_AGG: {
                            "min": {ElasticsearchQueryKeys.FIELD: SceneFinder.__SCENE_START_TIME},
                        },
                        SceneFinder.__SCENE_END_AGG: {
                            "max": {ElasticsearchQueryKeys.FIELD: SceneFinder.__SCENE_END_TIME},
                        },
                    },
                },
            },
        }

    @staticmethod
    def __extract_cuts_from_buckets(buckets: List[Dict[str, Any]]) -> List[float]:
        raw_cuts = []
        for bucket in buckets:
            start = bucket.get(SceneFinder.__SCENE_START_AGG, {}).get(ElasticsearchAggregationKeys.VALUE)
            end = bucket.get(SceneFinder.__SCENE_END_AGG, {}).get(ElasticsearchAggregationKeys.VALUE)
            if start is not None:
                raw_cuts.append(float(start))
            if end is not None:
                raw_cuts.append(float(end))
        return raw_cuts

    @staticmethod
    async def fetch_scene_cuts(
        series_name: str,
        season: int,
        episode_number: int,
        logger: logging.Logger,
    ) -> List[float]:
        try:
            es = await ElasticSearchManager.connect_to_elasticsearch(logger)
            index = f"{series_name}{ElasticsearchIndexSuffixes.TEXT_SEGMENTS}"
            query = SceneFinder.__build_scene_cuts_query(season, episode_number)
            response = await es.search(index=index, body=query)
            buckets = response[ElasticsearchKeys.AGGREGATIONS][SceneFinder.__UNIQUE_SCENES_AGG][ElasticsearchKeys.BUCKETS]
            raw_cuts = SceneFinder.__extract_cuts_from_buckets(buckets)
            scene_cuts = sorted(set(raw_cuts))
            await log_system_message(
                logging.INFO,
                f"Fetched {len(scene_cuts)} scene cuts for S{season:02d}E{episode_number:02d} in '{series_name}'",
                logger,
            )
            return scene_cuts
        except Exception as e:
            await log_system_message(logging.WARNING, f"Failed to fetch scene cuts: {e}", logger)
            return []
