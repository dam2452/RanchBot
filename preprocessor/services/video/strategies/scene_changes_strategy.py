from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.enums import FrameType
from preprocessor.config.types import FrameRequest
from preprocessor.services.ui.console import console
from preprocessor.services.video.strategies.base_strategy import BaseKeyframeStrategy


class SceneChangesStrategy(BaseKeyframeStrategy):
    def __init__(self, frames_per_scene: int, scene_change_offset_seconds: float = 0.5) -> None:
        self.__frames_per_scene = frames_per_scene
        self.__offset = scene_change_offset_seconds

    def extract_frame_requests(
        self, video_path: Path, data: Dict[str, Any],
    ) -> List[FrameRequest]:
        scenes = self.__extract_scenes(data)
        if not scenes:
            console.print('[yellow]No scene timestamps found[/yellow]')
            return []

        return self.__process_all_scenes(scenes)

    def __process_all_scenes(
        self, scenes: List[Dict[str, Any]],
    ) -> List[FrameRequest]:
        frame_requests: List[FrameRequest] = []
        for i, scene in enumerate(scenes):
            frame_requests.extend(self.__process_single_scene(scene, i))
        return frame_requests

    def __process_single_scene(
        self, scene: Dict[str, Any], scene_index: int,
    ) -> List[FrameRequest]:
        start_seconds = scene.get('start', {}).get('seconds', 0.0) + self.__offset
        end_seconds = scene.get('end', {}).get('seconds', start_seconds)
        duration = end_seconds - start_seconds

        if duration <= 0.1:
            return [
                self.__create_request(start_seconds, FrameType.SCENE_SINGLE, scene_index),
            ]

        return self.__generate_multi_frame_requests(
            start_seconds, duration, scene_index,
        )

    def __generate_multi_frame_requests(
        self, start_seconds: float, duration: float, scene_index: int,
    ) -> List[FrameRequest]:
        requests: List[FrameRequest] = []
        for frame_idx in range(self.__frames_per_scene):
            timestamp = self.__calculate_timestamp(
                start_seconds, duration, frame_idx,
            )
            frame_type = self.__determine_frame_type(frame_idx)
            requests.append(
                self.__create_request(timestamp, frame_type, scene_index),
            )
        return requests

    def __calculate_timestamp(
        self, start_seconds: float, duration: float, frame_idx: int,
    ) -> float:
        position = frame_idx / (self.__frames_per_scene - 1) if self.__frames_per_scene > 1 else 0.0
        return start_seconds + position * duration

    def __determine_frame_type(self, frame_idx: int) -> str:
        if frame_idx == 0:
            return FrameType.SCENE_START
        if frame_idx == self.__frames_per_scene - 1:
            return FrameType.SCENE_END
        return FrameType.scene_mid(frame_idx)

    @staticmethod
    def __extract_scenes(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        scene_timestamps = data.get('scene_timestamps', {})
        return scene_timestamps.get('scenes', [])

    @staticmethod
    def __create_request(
        timestamp: float, type_name: str, scene_num: Optional[int] = None,
    ) -> FrameRequest:
        req: FrameRequest = {
            'frame_number': 0,
            'timestamp': float(timestamp),
            'type': type_name,
        }
        if scene_num is not None:
            req['scene_number'] = scene_num
        return req
