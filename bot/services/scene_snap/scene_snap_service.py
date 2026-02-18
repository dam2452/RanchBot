import bisect
import logging
from typing import (
    List,
    Tuple,
    Union,
)

from bot.search.scene_finder import SceneFinder
from bot.types import (
    ClipSegment,
    ElasticsearchSegment,
)
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.utils.log import log_system_message


class SceneSnapService:
    __KEYFRAME_INTERVAL = 0.5

    @staticmethod
    def __apply_keyframe_offset(boundary: float, is_start: bool) -> float:
        if is_start:
            return boundary + SceneSnapService.__KEYFRAME_INTERVAL
        return boundary - SceneSnapService.__KEYFRAME_INTERVAL

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
        if valid_starts:
            nearest_start = min(valid_starts, key=lambda c: abs(c - clip_start))
            snapped_start = SceneSnapService.__apply_keyframe_offset(nearest_start, is_start=True)
        else:
            snapped_start = clip_start

        valid_ends = [c for c in scene_cuts if c >= speech_end]
        if valid_ends:
            nearest_end = min(valid_ends, key=lambda c: abs(c - clip_end))
            snapped_end = SceneSnapService.__apply_keyframe_offset(nearest_end, is_start=False)
        else:
            snapped_end = clip_end

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

            scene_cuts = await SceneFinder.fetch_scene_cuts(series_name, season, episode_number, logger)

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
                boundary = scene_cuts[0]
            else:
                target_idx = idx - offset_count
                boundary = scene_cuts[max(0, target_idx)]
            return SceneSnapService.__apply_keyframe_offset(boundary, is_start=True)

        idx = bisect.bisect_left(scene_cuts, reference_time)
        if idx >= len(scene_cuts):
            boundary = scene_cuts[-1]
        else:
            target_idx = idx + offset_count
            boundary = scene_cuts[min(len(scene_cuts) - 1, target_idx)]
        return SceneSnapService.__apply_keyframe_offset(boundary, is_start=False)
