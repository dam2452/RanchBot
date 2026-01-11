from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

import decord
import numpy as np

from preprocessor.config.config import settings
from preprocessor.core.enums import FrameType
from preprocessor.embeddings.strategies.base_strategy import BaseKeyframeStrategy
from preprocessor.utils.console import console
from preprocessor.utils.video_utils import iterate_frames_with_histogram


class ColorDiffStrategy(BaseKeyframeStrategy):
    def extract_frame_requests(
        self,
        video_path: Path,
        data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        vr = decord.VideoReader(str(video_path), ctx=decord.cpu(0))
        fps = vr.get_avg_fps()
        total_frames = len(vr)
        del vr

        console.print(f"[blue]Analyzing {total_frames} frames for color changes...[/blue]")
        frame_requests = []
        prev_hist = None

        for frame_num, _, hist in iterate_frames_with_histogram(str(video_path)):
            if prev_hist is not None:
                diff = np.sum(np.abs(hist - prev_hist))
                if diff > settings.keyframe_extraction.color_diff_threshold:
                    frame_requests.append(
                        self._create_request(frame_num, fps, FrameType.COLOR_CHANGE),
                    )

            prev_hist = hist

        console.print(f"[green]✓ Found {len(frame_requests)} color change frames[/green]")
        return frame_requests

    @staticmethod
    def _create_request(frame: int, fps: float, type_name: str) -> Dict[str, Any]:
        return {
            "frame_number": int(frame),
            "timestamp": float(frame / fps),
            "type": type_name,
        }
