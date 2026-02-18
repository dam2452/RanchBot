import logging
from typing import (
    Any,
    Dict,
    List,
)

from bot.search.elastic_search_manager import ElasticSearchManager
from bot.utils.constants import (
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EpisodeMetadataKeys,
)
from bot.utils.log import log_system_message


class SceneFinder:
    __SCENE_INFO_FIELD = "scene_info"
    __SCENE_NUMBER_FIELD = "scene_info.scene_number"
    __SCENE_START_TIME = "scene_info.scene_start_time"
    __SCENE_END_TIME = "scene_info.scene_end_time"
    __UNIQUE_SCENES_AGG = "unique_scenes"
    __SCENE_DATA_AGG = "scene_data"

    @staticmethod
    def __build_scene_cuts_query(season: int, episode_number: int) -> Dict[str, Any]:
        return {
            ElasticsearchQueryKeys.SIZE: 0,
            ElasticsearchQueryKeys.QUERY: {
                ElasticsearchQueryKeys.BOOL: {
                    ElasticsearchQueryKeys.MUST: [
                        {
                            ElasticsearchQueryKeys.TERM: {
                                f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.SEASON}": season,
                            },
                        },
                        {
                            ElasticsearchQueryKeys.TERM: {
                                f"{EpisodeMetadataKeys.EPISODE_METADATA}.{EpisodeMetadataKeys.EPISODE_NUMBER}": episode_number,
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
                        SceneFinder.__SCENE_DATA_AGG: {
                            ElasticsearchQueryKeys.TOP_HITS: {
                                ElasticsearchQueryKeys.SIZE: 1,
                                ElasticsearchQueryKeys.SOURCE: {
                                    ElasticsearchQueryKeys.INCLUDES: [
                                        SceneFinder.__SCENE_START_TIME,
                                        SceneFinder.__SCENE_END_TIME,
                                    ],
                                },
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def __extract_cuts_from_buckets(buckets: List[Dict[str, Any]]) -> List[float]:
        raw_cuts = []
        for bucket in buckets:
            hits = bucket[SceneFinder.__SCENE_DATA_AGG][ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
            if not hits:
                continue
            scene_info = hits[0][ElasticsearchKeys.SOURCE].get(SceneFinder.__SCENE_INFO_FIELD, {})
            start = scene_info.get("scene_start_time")
            end = scene_info.get("scene_end_time")
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
            index = f"{series_name}_text_segments"
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
