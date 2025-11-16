import json
from pathlib import Path
import sys

import pytest

from preprocessor.transcription_importer import TranscriptionImporter

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

SOURCE_DIR = Path(__file__).parent / "mock_11labs_data"
OUTPUT_DIR = Path(__file__).parent / "output" / "transcriptions_11labs"
EPISODES_INFO = Path(__file__).parent / "test_episodes_info.json"


@pytest.fixture(scope="module")
def mock_11labs_data():
    mock_transcription = {
        "segments": [
            {
                "start": 0.0,
                "end": 5.0,
                "text": "Test segment 1",
                "speaker": "SPEAKER_00",
                "words": [],
            },
            {
                "start": 5.0,
                "end": 10.0,
                "text": "Test segment 2",
                "speaker": "SPEAKER_01",
                "words": [],
            },
        ],
    }

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    mock_file = SOURCE_DIR / "test_S01E13.json"

    with open(mock_file, "w", encoding="utf-8") as f:
        json.dump(mock_transcription, f, indent=2)

    yield SOURCE_DIR

    import shutil
    shutil.rmtree(SOURCE_DIR, ignore_errors=True)


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


def test_elevenlabs_import(mock_11labs_data, episodes_info):
    importer = TranscriptionImporter({
        "source_dir": mock_11labs_data,
        "output_dir": OUTPUT_DIR,
        "episodes_info_json": episodes_info,
        "series_name": "test",
        "format_type": "11labs_segmented",
        "state_manager": None,
    })

    exit_code = importer.work()
    assert exit_code == 0, "11labs import failed"

    expected_output = OUTPUT_DIR / "Sezon 1" / "test_S01E13.json"
    assert expected_output.exists(), f"Output file not created: {expected_output}"

    with open(expected_output, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "transcription" in data, "Missing 'transcription' in output"
    assert "segments" in data, "Missing 'segments' in output"
    assert len(data["segments"]) > 0, "No segments in output"

    print(f"\n✓ Imported {len(data['segments'])} segments")
    print(f"✓ Transcription format: {data['transcription'].get('format', 'unknown')}")
