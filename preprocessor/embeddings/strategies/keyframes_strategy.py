from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

import decord

from preprocessor.config.config import settings
from preprocessor.core.enums import FrameType
from preprocessor.embeddings.strategies.base_strategy import BaseKeyframeStrategy


class KeyframesStrategy(BaseKeyframeStrategy):
    def __init__(self, keyframe_interval: int):
        self.keyframe_interval = keyframe_interval

    def extract_frame_requests(
        self,
        video_path: Path,
        data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))
        fps = vr.get_avg_fps()
        total_frames = len(vr)
        del vr

        interval_frames = int(fps * settings.embedding.keyframe_interval_multiplier)
        frame_requests = []

        keyframe_count = 0
        for frame_num in range(0, total_frames, interval_frames):
            if keyframe_count % self.keyframe_interval == 0:
                frame_requests.append(self._create_request(frame_num, fps, FrameType.KEYFRAME))
            keyframe_count += 1

        return frame_requests

    @staticmethod
    def _create_request(frame: int, fps: float, type_name: str) -> Dict[str, Any]:
        return {
            "frame_number": int(frame),
            "timestamp": float(frame / fps),
            "type": type_name,
        }
