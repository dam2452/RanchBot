from pathlib import Path
import sys

import pytest

from bot.utils.resolution import Resolution
from preprocessor.core.state_manager import StateManager
from preprocessor.video.video_transcoder import VideoTranscoder

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_ranczo_S01E13.mp4"
TEST_VIDEO_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent / "output" / "transcoded_videos"


@pytest.mark.transcoding
@pytest.mark.slow
def test_transcoding_single_episode(episodes_info_single, mock_state_manager):
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    transcoder = VideoTranscoder({
        "videos": TEST_VIDEO_DIR,
        "transcoded_videos": OUTPUT_DIR,
        "resolution": Resolution.from_str("144p"),
        "codec": "h264_nvenc",
        "preset": "fast",
        "crf": 28,
        "gop_size": 0.5,
        "episodes_info_json": episodes_info_single,
        "state_manager": mock_state_manager,
        "series_name": "test_ranczo",
        "max_workers": 1,
    })

    exit_code = transcoder.work()
    assert exit_code == 0, "Transcoding failed"

    expected_output = OUTPUT_DIR / "Sezon 1" / "test_ranczo_S01E01.mp4"
    assert expected_output.exists(), f"Transcoded video not created: {expected_output}"
    assert expected_output.stat().st_size > 0, "Transcoded video is empty"

    print(f"\nVideo transcoded: {expected_output}")
    print(f"File size: {expected_output.stat().st_size / (1024*1024):.2f} MB")


@pytest.mark.transcoding
@pytest.mark.slow
def test_transcoding_multiple_episodes(episodes_info_multiple, mock_state_manager):
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    transcoder = VideoTranscoder({
        "videos": TEST_VIDEO_DIR,
        "transcoded_videos": OUTPUT_DIR,
        "resolution": Resolution.from_str("240p"),
        "codec": "h264_nvenc",
        "preset": "fast",
        "crf": 28,
        "gop_size": 0.5,
        "episodes_info_json": episodes_info_multiple,
        "state_manager": mock_state_manager,
        "series_name": "test_ranczo",
        "max_workers": 1,
    })

    exit_code = transcoder.work()
    assert exit_code == 0, "Transcoding failed"

    expected_outputs = [
        OUTPUT_DIR / "Sezon 1" / "test_ranczo_S01E01.mp4",
    ]

    for expected_output in expected_outputs:
        assert expected_output.exists(), f"Transcoded video not created: {expected_output}"
        assert expected_output.stat().st_size > 0, f"Transcoded video is empty: {expected_output}"

        print(f"\nVideo transcoded: {expected_output}")
        print(f"File size: {expected_output.stat().st_size / (1024*1024):.2f} MB")


@pytest.mark.transcoding
@pytest.mark.slow
def test_transcoding_with_state_manager(episodes_info_single):
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    state_manager = StateManager(series_name="test_ranczo", working_dir=OUTPUT_DIR)

    transcoder = VideoTranscoder({
        "videos": TEST_VIDEO_DIR,
        "transcoded_videos": OUTPUT_DIR,
        "resolution": Resolution.from_str("144p"),
        "codec": "h264_nvenc",
        "preset": "fast",
        "crf": 28,
        "gop_size": 0.5,
        "episodes_info_json": episodes_info_single,
        "state_manager": state_manager,
        "series_name": "test_ranczo",
        "max_workers": 1,
    })

    exit_code = transcoder.work()
    assert exit_code == 0, "First transcoding failed"

    exit_code = transcoder.work()
    assert exit_code == 0, "Second transcoding (should skip) failed"

    state_manager.save_state()
    state_file = OUTPUT_DIR / ".preprocessing_state.json"
    assert state_file.exists(), "State file not created"

    print("\n✓ State manager test passed")
    print(f"State file: {state_file}")
