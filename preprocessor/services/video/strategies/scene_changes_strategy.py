from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.enums import FrameType
from preprocessor.services.ui.console import console
from preprocessor.services.video.strategies.base_strategy import BaseKeyframeStrategy


class SceneChangesStrategy(BaseKeyframeStrategy):
    def __init__(self, frames_per_scene: int) -> None:
        self.__frames_per_scene = frames_per_scene

    def extract_frame_requests(
        self, video_path: Path, data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        scenes = self.__extract_scenes(data)
        if not scenes:
            console.print('[yellow]No scene timestamps found[/yellow]')
            return []

        fps = self.__extract_fps(data)
        return self.__process_all_scenes(scenes, fps)

    def __process_all_scenes(
        self, scenes: List[Dict[str, Any]], fps: float,
    ) -> List[Dict[str, Any]]:
        frame_requests: List[Dict[str, Any]] = []
        for i, scene in enumerate(scenes):
            frame_requests.extend(self.__process_single_scene(scene, i, fps))
        return frame_requests

    def __process_single_scene(
        self, scene: Dict[str, Any], scene_index: int, fps: float,
    ) -> List[Dict[str, Any]]:
        start_frame = scene.get('start', {}).get('frame', 0)
        frame_count = scene.get('frame_count', 1)

        if frame_count <= 1:
            return [
                self.__create_request(start_frame, fps, FrameType.SCENE_SINGLE, scene_index),
            ]

        return self.__generate_multi_frame_requests(
            start_frame, frame_count, scene_index, fps,
        )

    def __generate_multi_frame_requests(
        self, start_frame: int, frame_count: int, scene_index: int, fps: float,
    ) -> List[Dict[str, Any]]:
        requests: List[Dict[str, Any]] = []
        for frame_idx in range(self.__frames_per_scene):
            frame_number = self.__calculate_frame_number(
                start_frame, frame_count, frame_idx,
            )
            frame_type = self.__determine_frame_type(frame_idx)
            requests.append(
                self.__create_request(frame_number, fps, frame_type, scene_index),
            )
        return requests

    def __calculate_frame_number(
        self, start_frame: int, frame_count: int, frame_idx: int,
    ) -> int:
        position = frame_idx / (self.__frames_per_scene - 1) if self.__frames_per_scene > 1 else 0.0
        return int(start_frame + position * (frame_count - 1))

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
    def __extract_fps(data: Dict[str, Any]) -> float:
        scene_timestamps = data.get('scene_timestamps', {})
        video_info = scene_timestamps.get('video_info', {})
        fps = video_info.get('fps')
        if fps is None:
            raise ValueError('FPS not found in scene_timestamps video_info')
        return fps

    @staticmethod
    def __create_request(
        frame: int, fps: float, type_name: str, scene_num: Optional[int] = None,
    ) -> Dict[str, Any]:
        req: Dict[str, Any] = {
            'frame_number': int(frame),
            'timestamp': float(frame / fps),
            'type': type_name,
        }
        if scene_num is not None:
            req['scene_number'] = scene_num
        return req
