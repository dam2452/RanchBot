from pathlib import Path
import sys

import pytest

from bot.utils.resolution import Resolution
from preprocessor.video.video_transcoder import VideoTranscoder

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_ranczo_S01E13.mp4"
TEST_VIDEO_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent / "output" / "transcoded_videos"


@pytest.mark.transcoding
def test_transcoding(episodes_info_single):
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    transcoder = VideoTranscoder({
        "videos": TEST_VIDEO_DIR,
        "transcoded_videos": OUTPUT_DIR,
        "resolution": Resolution.from_str("144p"),
        "codec": "h264_nvenc",
        "preset": "fast",
        "crf": 28,
        "gop_size": 0.5,
        "episodes_info_json": episodes_info_single,
        "state_manager": None,
        "series_name": "test_ranczo",
    })

    exit_code = transcoder.work()
    assert exit_code == 0, "Transcoding failed"

    expected_output = OUTPUT_DIR / "Sezon 1" / "test_ranczo_S01E01.mp4"
    assert expected_output.exists(), f"Transcoded video not created: {expected_output}"
    assert expected_output.stat().st_size > 0, "Transcoded video is empty"

    print(f"\nVideo transcoded: {expected_output}")
    print(f"File size: {expected_output.stat().st_size / (1024*1024):.2f} MB")
