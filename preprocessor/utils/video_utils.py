from typing import (
    Generator,
    Tuple,
)

import cv2
import numpy as np


def iterate_frames_with_histogram(
    video_path: str,
    sample_interval: int = 5,
) -> Generator[Tuple[int, np.ndarray, np.ndarray], None, None]:
    cap = cv2.VideoCapture(video_path)
    frame_num = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_num % sample_interval != 0:
            frame_num += 1
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()

        yield frame_num, frame, hist
        frame_num += 1

    cap.release()
