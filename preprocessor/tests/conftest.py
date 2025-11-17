import json
from pathlib import Path
from typing import List

import pytest

EPISODES_INFO_PATH = Path(__file__).parent / "test_episodes_info.json"
TRANSCRIPTION_DIR = Path(__file__).parent / "output" / "transcriptions" / "json"


def require_transcription_files() -> List[Path]:
    assert TRANSCRIPTION_DIR.exists(), (
        f"Transcription directory not found: {TRANSCRIPTION_DIR}. "
        "Run test_transcription.py first!"
    )

    transcription_files = list(TRANSCRIPTION_DIR.glob("**/*.json"))
    assert len(transcription_files) > 0, (
        f"No transcription files found in {TRANSCRIPTION_DIR}. "
        "Run test_transcription.py first!"
    )

    return transcription_files


@pytest.fixture(scope="module")
def episodes_info_single():
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

    EPISODES_INFO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EPISODES_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(episodes_info_data, f, indent=2, ensure_ascii=False)

    yield EPISODES_INFO_PATH

    EPISODES_INFO_PATH.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def episodes_info_multiple():
    episodes_info_data = {
        "seasons": [
            {
                "season_number": 1,
                "episodes": [
                    {
                        "episode_number": 1,
                        "title": "Test Episode S01E01",
                        "premiere_date": "2006-06-05",
                        "viewership": 5000000,
                    },
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

    EPISODES_INFO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EPISODES_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(episodes_info_data, f, indent=2, ensure_ascii=False)

    yield EPISODES_INFO_PATH

    EPISODES_INFO_PATH.unlink(missing_ok=True)
