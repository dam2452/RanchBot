import json
from pathlib import Path
import sys

import pytest

from preprocessor.processing.scene_detector import SceneDetector

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_ranczo_S01E13.mp4"
OUTPUT_DIR = Path(__file__).parent / "output" / "scene_timestamps"


@pytest.mark.slow
def test_scene_detection():
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    detector = SceneDetector({
        "videos": TEST_VIDEO,
        "output_dir": OUTPUT_DIR,
        "threshold": 0.5,
        "min_scene_len": 10,
        "device": "cuda",
    })

    exit_code = detector.work()
    assert exit_code == 0, "Scene detection failed"

    output_file = OUTPUT_DIR / f"{TEST_VIDEO.stem}_scenes.json"
    assert output_file.exists(), f"Output file not created: {output_file}"

    with open(output_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "total_scenes" in data, "Missing 'total_scenes' in output"
    assert data["total_scenes"] > 0, "No scenes detected"
    assert "scenes" in data, "Missing 'scenes' in output"
    assert "video_info" in data, "Missing 'video_info' in output"
    assert "detection_settings" in data, "Missing 'detection_settings' in output"

    assert data["video_info"]["fps"] > 0, "Invalid FPS in video_info"
    assert data["video_info"]["total_frames"] > 0, "Invalid total_frames in video_info"
    assert data["detection_settings"]["threshold"] == 0.5, "Threshold mismatch"
    assert data["detection_settings"]["min_scene_len"] == 10, "min_scene_len mismatch"

    for scene in data["scenes"]:
        assert "scene_number" in scene, "Missing 'scene_number' in scene"
        assert "start" in scene, "Missing 'start' in scene"
        assert "end" in scene, "Missing 'end' in scene"
        assert "duration" in scene, "Missing 'duration' in scene"
        assert "frame_count" in scene, "Missing 'frame_count' in scene"

        assert scene["start"]["frame"] >= 0, "Invalid start frame"
        assert scene["end"]["frame"] > scene["start"]["frame"], "End frame before start frame"
        assert scene["duration"] > 0, "Invalid duration"
        assert scene["frame_count"] > 0, "Invalid frame_count"

    print(f"\nTotal scenes detected: {data['total_scenes']}")
    print(f"Detection method: {data['detection_settings']['method']}")
    print(f"Video FPS: {data['video_info']['fps']:.2f}")
    print(f"Video duration: {data['video_info']['duration']:.2f}s")
