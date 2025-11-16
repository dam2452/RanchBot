import json
from pathlib import Path
import sys

import pytest

from preprocessor.elevenlabs_transcriber import ElevenLabsTranscriber

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_video.mp4"
TEST_VIDEO_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent / "output" / "transcriptions_elevenlabs_api"
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


@pytest.mark.skip(reason="11labs API test - requires API key. Run manually with: pytest test_elevenlabs_api.py --api-key=YOUR_KEY")
@pytest.mark.elevenlabs_api
def test_elevenlabs_api_transcription(request, episodes_info):
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    api_key = request.config.getoption("--api-key", default=None)
    if not api_key:
        pytest.skip("No API key provided. Use --api-key=YOUR_KEY")

    transcriber = ElevenLabsTranscriber({
        "videos": TEST_VIDEO_DIR,
        "output_dir": OUTPUT_DIR,
        "episodes_info_json": episodes_info,
        "series_name": "test_ranczo",
        "api_key": api_key,
        "model_id": "scribe_v1",
        "language_code": "pol",
        "diarize": True,
        "state_manager": None,
    })

    exit_code = transcriber.work()
    assert exit_code == 0, "11labs API transcription failed"

    expected_output = OUTPUT_DIR / "Sezon 1" / "test_ranczo_S01E13.json"
    assert expected_output.exists(), f"Output file not created: {expected_output}"

    with open(expected_output, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "transcription" in data, "Missing 'transcription' in output"
    assert "segments" in data, "Missing 'segments' in output"
    assert len(data["segments"]) > 0, "No segments generated"

    has_speakers = any(
        seg.get("speaker") and seg["speaker"] != "unknown"
        for seg in data["segments"]
    )

    print(f"\n✓ Total segments: {len(data['segments'])}")
    print(f"✓ Speaker diarization: {'Yes' if has_speakers else 'No'}")
    print(f"✓ Transcription format: {data['transcription'].get('format', 'unknown')}")


def pytest_addoption(parser):
    parser.addoption(
        "--api-key",
        action="store",
        default=None,
        help="11labs API key for testing",
    )
