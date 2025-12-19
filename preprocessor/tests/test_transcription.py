import json
from pathlib import Path
import sys

import pytest

from preprocessor.transcriptions.transcription_generator import TranscriptionGenerator

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_ranczo_S01E13.mp4"
TEST_VIDEO_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent / "output" / "transcriptions"


@pytest.mark.slow
@pytest.mark.transcription
def test_transcription_generation(episodes_info_multiple):  # pylint: disable=too-many-statements
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generator = TranscriptionGenerator({
        "videos": TEST_VIDEO_DIR,
        "episodes_info_json": episodes_info_multiple,
        "transcription_jsons": OUTPUT_DIR,
        "model": "base",
        "language": "Polish",
        "device": "cuda",
        "name": "test_ranczo",
        "ramdisk_path": None,
    })

    exit_code = generator.work()
    assert exit_code == 0, "Transcription generation failed"

    expected_json = OUTPUT_DIR / "json" / "Sezon 1" / "test_ranczo_S01E01.json"
    expected_segmented = OUTPUT_DIR / "segmented_json" / "Sezon 1" / "test_ranczo_S01E01_segmented.json"
    expected_simple = OUTPUT_DIR / "simple_json" / "Sezon 1" / "test_ranczo_S01E01_simple.json"
    expected_srt = OUTPUT_DIR / "srt" / "Sezon 1" / "test_ranczo_S01E01.srt"
    expected_txt = OUTPUT_DIR / "txt" / "Sezon 1" / "test_ranczo_S01E01.txt"

    assert expected_json.exists(), f"Full JSON not created: {expected_json}"
    assert expected_segmented.exists(), f"Segmented JSON not created: {expected_segmented}"
    assert expected_simple.exists(), f"Simple JSON not created: {expected_simple}"
    assert expected_srt.exists(), f"SRT not created: {expected_srt}"
    assert expected_txt.exists(), f"TXT not created: {expected_txt}"

    with open(expected_json, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    assert "words" in json_data, "Missing 'words' in full JSON"
    assert "text" in json_data, "Missing 'text' in full JSON"
    assert "episode_info" in json_data, "Missing 'episode_info' in full JSON"
    assert "segments" in json_data, "Missing 'segments' in full JSON"

    episode_info = json_data["episode_info"]
    assert episode_info["season"] == 1, "Incorrect season in episode_info"
    assert episode_info["episode_number"] == 1, "Incorrect episode_number in episode_info"
    assert "title" in episode_info, "Missing 'title' in episode_info"

    with open(expected_segmented, "r", encoding="utf-8") as f:
        seg_data = json.load(f)
    assert "segments" in seg_data, "Missing 'segments' in segmented JSON"
    assert len(seg_data["segments"]) > 0, "No segments in segmented JSON"

    for seg in seg_data["segments"]:
        assert "id" in seg, "Missing 'id' in segment"
        assert "start" in seg, "Missing 'start' in segment"
        assert "end" in seg, "Missing 'end' in segment"
        assert "text" in seg, "Missing 'text' in segment"

    with open(expected_simple, "r", encoding="utf-8") as f:
        simple_data = json.load(f)
    assert "segments" in simple_data, "Missing 'segments' in simple JSON"
    assert len(simple_data["segments"]) > 0, "No segments in simple JSON"

    with open(expected_srt, "r", encoding="utf-8") as f:
        srt_content = f.read()
    assert len(srt_content) > 0, "SRT file is empty"
    assert "-->" in srt_content, "SRT file missing timestamp markers"

    with open(expected_txt, "r", encoding="utf-8") as f:
        txt_content = f.read()
    assert len(txt_content) > 0, "TXT file is empty"

    print("\nGenerated all 5 formats successfully:")
    print(f"  - Full JSON: {len(json_data.get('words', []))} words, {len(json_data['segments'])} segments")
    print(f"  - Segmented JSON: {len(seg_data['segments'])} segments")
    print(f"  - Simple JSON: {len(simple_data['segments'])} segments")
    print(f"  - SRT: {len(srt_content)} chars")
    print(f"  - TXT: {len(txt_content)} chars")


@pytest.mark.slow
@pytest.mark.transcription
def test_transcription_output_structure(episodes_info_single):
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generator = TranscriptionGenerator({
        "videos": TEST_VIDEO_DIR,
        "episodes_info_json": episodes_info_single,
        "transcription_jsons": OUTPUT_DIR,
        "model": "base",
        "language": "Polish",
        "device": "cuda",
        "name": "test_ranczo",
        "ramdisk_path": None,
    })

    exit_code = generator.work()
    assert exit_code == 0, "Transcription generation failed"

    expected_json = OUTPUT_DIR / "json" / "Sezon 1" / "test_ranczo_S01E01.json"
    assert expected_json.exists(), f"Full JSON not created: {expected_json}"

    with open(expected_json, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    required_keys = ["text", "segments", "language", "episode_info", "words"]
    for key in required_keys:
        assert key in json_data, f"Missing required key '{key}' in full JSON"

    assert isinstance(json_data["segments"], list), "'segments' should be a list"
    assert isinstance(json_data["words"], list), "'words' should be a list"
    assert len(json_data["segments"]) > 0, "No segments in transcription"
    assert len(json_data["words"]) > 0, "No words in transcription"

    print("\n✓ Transcription structure validated successfully")
    print(f"Total segments: {len(json_data['segments'])}")
    print(f"Total words: {len(json_data['words'])}")
