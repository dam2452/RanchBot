from typing import (
    Generator,
    Tuple,
)

import decord
import numpy as np


def iterate_frames_with_histogram(
    video_path: str,
    sample_interval: int = 5,
) -> Generator[Tuple[int, np.ndarray, np.ndarray], None, None]:
    vr = decord.VideoReader(video_path, ctx=decord.cpu(0))
    total_frames = len(vr)

    for frame_num in range(0, total_frames, sample_interval):
        try:
            frame_tensor = vr[frame_num]
            frame_np = frame_tensor.numpy()

            gray = np.dot(frame_np[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)
            hist, _ = np.histogram(gray, bins=256, range=(0, 256))
            hist = hist / (hist.sum() + 1e-7)

            yield frame_num, frame_np, hist

        except (RuntimeError, ValueError, OSError):
            break
