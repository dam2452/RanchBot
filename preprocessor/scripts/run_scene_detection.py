#!/usr/bin/env python3
import sys
from pathlib import Path

from preprocessor.processing.scene_detector import SceneDetector

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run_scene_detection.py <video_file_or_dir>")
        sys.exit(1)

    videos = Path(sys.argv[1])

    detector = SceneDetector({
        "videos": videos,
        "output_dir": Path("/app/output_data/scene_timestamps"),
        "threshold": 0.5,
        "min_scene_len": 10,
    })

    exit_code = detector.work()
    sys.exit(exit_code)
