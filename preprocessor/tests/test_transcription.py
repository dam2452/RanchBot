import json
from pathlib import Path
import sys

from preprocessor.transcriptions.transcription_generator import TranscriptionGenerator

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_ranczo_S01E13.mp4"
TEST_VIDEO_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent / "output" / "transcriptions"


def test_transcription(episodes_info_multiple):
    assert TEST_VIDEO.exists(), f"Test video not found: {TEST_VIDEO}"

    generator = TranscriptionGenerator({
        "videos": TEST_VIDEO_DIR,
        "episodes_info_json": episodes_info_multiple,
        "transcription_jsons": OUTPUT_DIR,
        "model": "base",
        "language": "Polish",
        "device": "cuda",
        "extra_json_keys_to_remove": [],
        "name": "test_ranczo",
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

    with open(expected_segmented, "r", encoding="utf-8") as f:
        seg_data = json.load(f)
    assert "segments" in seg_data, "Missing 'segments' in segmented JSON"
    assert len(seg_data["segments"]) > 0, "No segments in segmented JSON"

    with open(expected_simple, "r", encoding="utf-8") as f:
        simple_data = json.load(f)
    assert "segments" in simple_data, "Missing 'segments' in simple JSON"

    with open(expected_srt, "r", encoding="utf-8") as f:
        srt_content = f.read()
    assert len(srt_content) > 0, "SRT file is empty"
    assert "-->" in srt_content, "SRT file missing timestamp markers"

    with open(expected_txt, "r", encoding="utf-8") as f:
        txt_content = f.read()
    assert len(txt_content) > 0, "TXT file is empty"

    print("\nGenerated all 5 formats successfully:")
    print(f"  - Full JSON: {len(json_data.get('words', []))} words")
    print(f"  - Segmented JSON: {len(seg_data['segments'])} segments")
    print(f"  - Simple JSON: {len(simple_data['segments'])} segments")
    print(f"  - SRT: {len(srt_content)} chars")
    print(f"  - TXT: {len(txt_content)} chars")
