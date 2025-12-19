import json
from pathlib import Path
import sys

import pytest

from preprocessor.transcriptions.elevenlabs_transcriber import ElevenLabsTranscriber

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_video.mp4"
TEST_VIDEO_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent / "output" / "transcriptions_elevenlabs_api"


@pytest.mark.skip(reason="11labs API test - requires API key. Run manually with: ELEVEN_API_KEY=YOUR_KEY pytest test_elevenlabs_api.py")
@pytest.mark.elevenlabs_api
def test_elevenlabs_api_transcription(episodes_info_single):
    import os
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    if not os.getenv("ELEVEN_API_KEY"):
        pytest.skip("No API key provided. Set ELEVEN_API_KEY environment variable")

    transcriber = ElevenLabsTranscriber({
        "videos": TEST_VIDEO_DIR,
        "output_dir": OUTPUT_DIR,
        "episodes_info_json": episodes_info_single,
        "series_name": "test_ranczo",
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


