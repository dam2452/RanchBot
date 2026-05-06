from bisect import (
    bisect_left,
    bisect_right,
)
import logging
from typing import (
    Any,
    Dict,
    List,
)


class ScenesMerger:
    def __init__(self, logger: logging.Logger) -> None:
        self.__logger = logger

    def merge(
        self,
        text_segments: List[Dict[str, Any]],
        video_frames: List[Dict[str, Any]],
        frame_before: float = 0.0,
        frame_after: float = 0.0,
    ) -> List[Dict[str, Any]]:
        sorted_frames = sorted(
            (f for f in video_frames if f.get("timestamp") is not None),
            key=lambda f: float(f["timestamp"]),
        )
        timestamps = [float(f["timestamp"]) for f in sorted_frames]

        scenes = []
        for segment in text_segments:
            start = float(segment.get("start_time", 0.0))
            end = float(segment.get("end_time", 0.0))

            lo = bisect_left(timestamps, max(0.0, start - frame_before))
            hi = bisect_right(timestamps, end + frame_after)
            segment_frames = [
                self.__build_frame(sorted_frames[i]) for i in range(lo, hi)
            ]

            scene = self.__build_scene(segment, segment_frames)
            scenes.append(scene)

        self.__logger.debug(
            "ScenesMerger: %d segments + %d frames → %d scenes",
            len(text_segments),
            len(video_frames),
            len(scenes),
        )
        return scenes

    @staticmethod
    def __build_frame(frame: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "frame_number": frame.get("frame_number"),
            "timestamp": frame.get("timestamp"),
            "frame_type": frame.get("frame_type"),
            "scene_number": frame.get("scene_number"),
            "scene_info": frame.get("scene_info"),
            "perceptual_hash": frame.get("perceptual_hash"),
            "perceptual_hash_int": frame.get("perceptual_hash_int"),
            "video_embedding": frame.get("video_embedding"),
        }
        character_appearances = frame.get("character_appearances")
        if character_appearances:
            result["character_appearances"] = character_appearances
        detected_objects = frame.get("detected_objects")
        if detected_objects:
            result["detected_objects"] = detected_objects
        return {k: v for k, v in result.items() if v is not None}

    @staticmethod
    def __build_scene(
        segment: Dict[str, Any],
        frames: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        scene: Dict[str, Any] = {
            "episode_id": segment.get("episode_id"),
            "episode_metadata": segment.get("episode_metadata"),
            "segment_id": segment.get("segment_id"),
            "text": segment.get("text"),
            "start_time": segment.get("start_time"),
            "end_time": segment.get("end_time"),
            "speaker": segment.get("speaker"),
            "video_path": segment.get("video_path"),
            "scene_info": segment.get("scene_info"),
            "frames": frames,
        }
        return {k: v for k, v in scene.items() if v is not None}
