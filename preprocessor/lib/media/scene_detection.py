import gc
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import decord
import numpy as np
import torch
from transnetv2_pytorch import TransNetV2


class TransNetWrapper:

    def __init__(self):
        self.model: Optional[TransNetV2] = None

    def load_model(self) -> None:
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA not available')
        self.model = TransNetV2().cuda()

    def detect_scenes(
        self,
        video_path: Path,
        threshold: float=0.5,
        min_scene_len: int=15,
    ) -> List[Dict[str, Any]]:
        if self.model is None:
            raise RuntimeError('Model not loaded. Call load_model() first.')
        video_info = self.get_video_info(video_path)
        if not video_info:
            raise RuntimeError(f'Failed to get video info for {video_path}')
        try:
            _, single_frame_predictions, _ = self.model.predict_video(str(video_path))
            scene_changes = np.where(single_frame_predictions > threshold)[0]
            return self._build_scenes_from_predictions(
                scene_changes,
                video_info,
                min_scene_len,
            )
        except (RuntimeError, ValueError, OSError) as e:
            raise RuntimeError(f'TransNetV2 detection failed: {e}') from e

    def _build_scenes_from_predictions(
        self,
        scene_changes: np.ndarray,
        video_info: Dict[str, Any],
        min_scene_len: int,
    ) -> List[Dict[str, Any]]:
        """Build scene list from frame predictions."""
        scenes = []
        fps = video_info['fps']
        prev_frame = 0
        for frame_num in scene_changes:
            if frame_num - prev_frame < min_scene_len:
                continue
            scene = self._create_scene_dict(len(scenes) + 1, prev_frame, frame_num, fps)
            scenes.append(scene)
            prev_frame = frame_num
        total_frames = video_info['total_frames']
        if total_frames - prev_frame > min_scene_len:
            scene = self._create_scene_dict(len(scenes) + 1, prev_frame, total_frames, fps)
            scenes.append(scene)
        return scenes

    @staticmethod
    def get_video_info(video_file: Path) -> Optional[Dict[str, Any]]:
        try:
            vr = decord.VideoReader(str(video_file), ctx=decord.cpu(0))
            fps = vr.get_avg_fps()
            total_frames = len(vr)
            duration = total_frames / fps if fps > 0 else 0
            return {'fps': fps, 'duration': duration, 'total_frames': total_frames}
        except (RuntimeError, ValueError, OSError):
            return None

    def cleanup(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _create_scene_dict(
        self,
        scene_number: int,
        start_frame: int,
        end_frame: int,
        fps: float,
    ) -> Dict[str, Any]:
        return {
            'scene_number': scene_number,
            'start': {
                'frame': int(start_frame),
                'seconds': float(start_frame / fps),
                'timecode': self._frame_to_timecode(start_frame, fps),
            },
            'end': {
                'frame': int(end_frame),
                'seconds': float(end_frame / fps),
                'timecode': self._frame_to_timecode(end_frame, fps),
            },
            'duration': float((end_frame - start_frame) / fps),
            'frame_count': int(end_frame - start_frame),
        }

    @staticmethod
    def _frame_to_timecode(frame: int, fps: float) -> str:
        seconds = frame / fps
        hours = int(seconds // 3600)
        minutes = int(seconds % 3600 // 60)
        secs = int(seconds % 60)
        frames = int(seconds % 1 * fps)
        return f'{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}'
