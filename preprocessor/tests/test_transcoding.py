import json
from pathlib import Path
import sys

import pytest

from bot.utils.resolution import Resolution
from preprocessor.video_transcoder import VideoTranscoder

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_ranczo_S01E13.mp4"
TEST_VIDEO_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent / "output" / "transcoded_videos"
EPISODES_INFO = Path(__file__).parent / "test_episodes_info.json"


@pytest.fixture(scope="module")
def episodes_info():
    episodes_info_data = {
        "seasons": [
            {
                "season_number": 1,
                "episodes": [
                    {
                        "episode_number": 13,
                        "title": "Test Episode S01E13",
                        "premiere_date": "2006-06-05",
                        "viewership": 5000000,
                    },
                ],
            },
        ],
    }

    EPISODES_INFO.parent.mkdir(parents=True, exist_ok=True)
    with open(EPISODES_INFO, "w", encoding="utf-8") as f:
        json.dump(episodes_info_data, f, indent=2, ensure_ascii=False)

    yield EPISODES_INFO

    EPISODES_INFO.unlink(missing_ok=True)


@pytest.mark.transcoding
def test_transcoding(episodes_info):
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    transcoder = VideoTranscoder({
        "videos": TEST_VIDEO_DIR,
        "transcoded_videos": OUTPUT_DIR,
        "resolution": Resolution.from_str("144p"),
        "codec": "h264_nvenc",
        "preset": "fast",
        "crf": 28,
        "gop_size": 0.5,
        "episodes_info_json": episodes_info,
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
