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
    __MAX_EXPANSION = 5.0
    __MAX_SHRINK = 2.0

    @staticmethod
    def __apply_keyframe_offset(boundary: float, is_start: bool) -> float:
        if is_start:
            return boundary + SceneSnapService.__KEYFRAME_INTERVAL
        return boundary - SceneSnapService.__KEYFRAME_INTERVAL

    @staticmethod
    def __snap_start(
        clip_start: float,
        speech_start: float,
        scene_cuts: List[float],
    ) -> float:
        def __snapped(c: float) -> float:
            return SceneSnapService.__apply_keyframe_offset(c, is_start=True)

        valid = [
            c for c in scene_cuts
            if c <= speech_start and __snapped(c) <= speech_start
        ]

        expanding = [
            c for c in valid
            if __snapped(c) <= clip_start
            and clip_start - __snapped(c) <= SceneSnapService.__MAX_EXPANSION
        ]
        if expanding:
            return __snapped(min(expanding, key=lambda c: abs(__snapped(c) - clip_start)))

        shrinking = [
            c for c in valid
            if __snapped(c) > clip_start
            and __snapped(c) - clip_start <= SceneSnapService.__MAX_SHRINK
        ]
        if shrinking:
            return __snapped(min(shrinking, key=lambda c: abs(__snapped(c) - clip_start)))

        return clip_start

    @staticmethod
    def __snap_end(
        clip_end: float,
        speech_end: float,
        scene_cuts: List[float],
    ) -> float:
        def __snapped(c: float) -> float:
            return SceneSnapService.__apply_keyframe_offset(c, is_start=False)

        valid = [
            c for c in scene_cuts
            if c >= speech_end and __snapped(c) >= speech_end
        ]

        expanding = [
            c for c in valid
            if __snapped(c) >= clip_end
            and __snapped(c) - clip_end <= SceneSnapService.__MAX_EXPANSION
        ]
        if expanding:
            return __snapped(min(expanding, key=lambda c: abs(__snapped(c) - clip_end)))

        shrinking = [
            c for c in valid
            if __snapped(c) < clip_end
            and clip_end - __snapped(c) <= SceneSnapService.__MAX_SHRINK
        ]
        if shrinking:
            return __snapped(min(shrinking, key=lambda c: abs(__snapped(c) - clip_end)))

        return clip_end

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

        snapped_start = SceneSnapService.__snap_start(clip_start, speech_start, scene_cuts)
        snapped_end = SceneSnapService.__snap_end(clip_end, speech_end, scene_cuts)
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
