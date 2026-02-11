from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.enums import FrameType
from preprocessor.lib.ui.console import console
from preprocessor.lib.video.strategies.base_strategy import BaseKeyframeStrategy


class SceneChangesStrategy(BaseKeyframeStrategy):

    def __init__(self, frames_per_scene: int):
        self.frames_per_scene = frames_per_scene

    def extract_frame_requests(self, video_path: Path, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        scene_timestamps = data.get('scene_timestamps', {})
        scenes = scene_timestamps.get('scenes', [])
        if not scenes:
            console.print('[yellow]No scene timestamps found[/yellow]')
            return []
        video_info = scene_timestamps.get('video_info', {})
        fps = video_info.get('fps')
        if fps is None:
            raise ValueError('FPS not found in scene_timestamps video_info')
        frame_requests = []
        for i, scene in enumerate(scenes):
            start_frame = scene.get('start', {}).get('frame', 0)
            frame_count = scene.get('frame_count', 1)
            if frame_count <= 1:
                frame_requests.append(self.__create_request(start_frame, fps, FrameType.SCENE_SINGLE, i))
                continue
            for frame_idx in range(self.frames_per_scene):
                position = frame_idx / (self.frames_per_scene - 1) if self.frames_per_scene > 1 else 0.0
                frame_number = int(start_frame + position * (frame_count - 1))
                if frame_idx == 0:
                    frame_type = FrameType.SCENE_START
                elif frame_idx == self.frames_per_scene - 1:
                    frame_type = FrameType.SCENE_END
                else:
                    frame_type = FrameType.scene_mid(frame_idx)
                frame_requests.append(self.__create_request(frame_number, fps, frame_type, i))
        return frame_requests

    @staticmethod
    def __create_request(frame: int, fps: float, type_name: str, scene_num: int=None) -> Dict[str, Any]:
        req = {'frame_number': int(frame), 'timestamp': float(frame / fps), 'type': type_name}
        if scene_num is not None:
            req['scene_number'] = scene_num
        return req
