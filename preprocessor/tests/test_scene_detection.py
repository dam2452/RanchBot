import json
from pathlib import Path
import sys

from preprocessor.processing.scene_detector import SceneDetector

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_ranczo_S01E13.mp4"
OUTPUT_DIR = Path(__file__).parent / "output" / "scene_timestamps"


def test_scene_detection():
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

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

    print(f"\nTotal scenes detected: {data['total_scenes']}")
