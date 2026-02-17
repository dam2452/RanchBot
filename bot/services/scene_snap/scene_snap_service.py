import bisect
import logging
from typing import (
    List,
    Tuple,
    Union,
)

from bot.search.elastic_search_manager import ElasticSearchManager
from bot.types import (
    ClipSegment,
    ElasticsearchSegment,
)
from bot.utils.constants import (
    ElasticsearchKeys,
    ElasticsearchQueryKeys,
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.utils.log import log_system_message

_SCENE_INFO_FIELD = "scene_info"
_SCENE_NUMBER_FIELD = "scene_info.scene_number"
_SCENE_START_TIME = "scene_info.scene_start_time"
_SCENE_END_TIME = "scene_info.scene_end_time"
_UNIQUE_SCENES_AGG = "unique_scenes"
_SCENE_DATA_AGG = "scene_data"


class SceneSnapService:
    @staticmethod
    def _build_scene_cuts_query(season: int, episode_number: int) -> dict:
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
                        {"exists": {"field": _SCENE_INFO_FIELD}},
                    ],
                },
            },
            ElasticsearchQueryKeys.AGGS: {
                _UNIQUE_SCENES_AGG: {
                    ElasticsearchQueryKeys.TERMS: {
                        ElasticsearchQueryKeys.FIELD: _SCENE_NUMBER_FIELD,
                        ElasticsearchQueryKeys.SIZE: 2000,
                    },
                    ElasticsearchQueryKeys.AGGS: {
                        _SCENE_DATA_AGG: {
                            ElasticsearchQueryKeys.TOP_HITS: {
                                ElasticsearchQueryKeys.SIZE: 1,
                                ElasticsearchQueryKeys.SOURCE: {
                                    ElasticsearchQueryKeys.INCLUDES: [
                                        _SCENE_START_TIME,
                                        _SCENE_END_TIME,
                                    ],
                                },
                            },
                        },
                    },
                },
            },
        }

    @staticmethod
    def _extract_cuts_from_buckets(buckets: list) -> List[float]:
        raw_cuts: List[float] = []
        for bucket in buckets:
            hits = bucket[_SCENE_DATA_AGG][ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]
            if not hits:
                continue
            scene_info = hits[0][ElasticsearchKeys.SOURCE].get(_SCENE_INFO_FIELD, {})
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
            query = SceneSnapService._build_scene_cuts_query(season, episode_number)
            response = await es.search(index=index, body=query)
            buckets = response[ElasticsearchKeys.AGGREGATIONS][_UNIQUE_SCENES_AGG][ElasticsearchKeys.BUCKETS]
            raw_cuts = SceneSnapService._extract_cuts_from_buckets(buckets)
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

    @staticmethod
    def snap_boundaries(
        clip_start: float,
        clip_end: float,
        speech_start: float,
        speech_end: float,
        scene_cuts: List[float],
    ) -> Tuple[float, float]:
        if not scene_cuts:
            return clip_start, clip_end

        valid_starts = [c for c in scene_cuts if c <= speech_start]
        snapped_start = min(valid_starts, key=lambda c: abs(c - clip_start)) if valid_starts else clip_start

        valid_ends = [c for c in scene_cuts if c >= speech_end]
        snapped_end = min(valid_ends, key=lambda c: abs(c - clip_end)) if valid_ends else clip_end

        return snapped_start, snapped_end

    @staticmethod
    async def snap_clip_times(
        series_name: str,
        segment: Union[ElasticsearchSegment, ClipSegment],
        clip_start: float,
        clip_end: float,
        logger: logging.Logger,
    ) -> Tuple[float, float]:
        try:
            episode_metadata = segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
            season = episode_metadata.get(EpisodeMetadataKeys.SEASON)
            episode_number = episode_metadata.get(EpisodeMetadataKeys.EPISODE_NUMBER)

            if season is None or episode_number is None:
                await log_system_message(logging.WARNING, "Missing episode metadata for scene snap", logger)
                return clip_start, clip_end

            scene_cuts = await SceneSnapService.fetch_scene_cuts(series_name, season, episode_number, logger)

            if not scene_cuts:
                return clip_start, clip_end

            speech_start = float(segment.get(SegmentKeys.START_TIME, clip_start))
            speech_end = float(segment.get(SegmentKeys.END_TIME, clip_end))

            return SceneSnapService.snap_boundaries(clip_start, clip_end, speech_start, speech_end, scene_cuts)

        except Exception as e:
            await log_system_message(logging.WARNING, f"Scene snap failed, using original times: {e}", logger)
            return clip_start, clip_end

    @staticmethod
    def find_boundary_by_cut_offset(
        scene_cuts: List[float],
        reference_time: float,
        offset_count: int,
        direction: str,
    ) -> float:
        if not scene_cuts:
            return reference_time

        if direction == "back":
            idx = bisect.bisect_right(scene_cuts, reference_time) - 1
            if idx < 0:
                return scene_cuts[0]
            target_idx = idx - offset_count
            return scene_cuts[max(0, target_idx)]

        idx = bisect.bisect_left(scene_cuts, reference_time)
        if idx >= len(scene_cuts):
            return scene_cuts[-1]
        target_idx = idx + offset_count
        return scene_cuts[min(len(scene_cuts) - 1, target_idx)]
