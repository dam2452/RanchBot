import json
from pathlib import Path
import sys

import pytest

from preprocessor.core.state_manager import StateManager

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

STATE_FILE = Path(__file__).parent / "output" / "test_state.json"


@pytest.fixture
def clean_state_file():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    yield STATE_FILE
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def test_state_manager_initialization(clean_state_file):
    manager = StateManager(clean_state_file)

    assert manager.state_file == clean_state_file
    assert not clean_state_file.exists(), "State file should not exist before save"


def test_state_manager_mark_step_completed(clean_state_file):
    manager = StateManager(clean_state_file)

    assert not manager.is_step_completed("transcode", "E01")

    manager.mark_step_started("transcode", "E01")
    assert not manager.is_step_completed("transcode", "E01")

    manager.mark_step_completed("transcode", "E01")
    assert manager.is_step_completed("transcode", "E01")


def test_state_manager_multiple_steps(clean_state_file):
    manager = StateManager(clean_state_file)

    episodes = ["E01", "E02", "E03"]
    steps = ["transcode", "transcription", "embeddings"]

    for episode in episodes:
        for step in steps:
            assert not manager.is_step_completed(step, episode)
            manager.mark_step_started(step, episode)
            manager.mark_step_completed(step, episode)
            assert manager.is_step_completed(step, episode)

    for episode in episodes:
        for step in steps:
            assert manager.is_step_completed(step, episode)


def test_state_manager_save_and_load(clean_state_file):
    manager1 = StateManager(clean_state_file)

    manager1.mark_step_completed("transcode", "E01")
    manager1.mark_step_completed("transcription", "E02")
    manager1.save()

    assert clean_state_file.exists(), "State file should exist after save"

    manager2 = StateManager(clean_state_file)

    assert manager2.is_step_completed("transcode", "E01")
    assert manager2.is_step_completed("transcription", "E02")
    assert not manager2.is_step_completed("embeddings", "E03")


def test_state_manager_persistence(clean_state_file):
    manager1 = StateManager(clean_state_file)
    manager1.mark_step_completed("transcode", "E01")
    manager1.mark_step_completed("transcode", "E02")
    manager1.save()

    with open(clean_state_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "transcode" in data
    assert "E01" in data["transcode"]
    assert "E02" in data["transcode"]
    assert data["transcode"]["E01"] == "completed"
    assert data["transcode"]["E02"] == "completed"


def test_state_manager_overwrite_protection(clean_state_file):
    manager = StateManager(clean_state_file)

    manager.mark_step_completed("transcode", "E01")
    assert manager.is_step_completed("transcode", "E01")

    manager.mark_step_started("transcode", "E01")
    assert manager.is_step_completed("transcode", "E01"), "Completed status should not be overwritten by started"


def test_state_manager_multiple_instances(clean_state_file):
    manager1 = StateManager(clean_state_file)
    manager1.mark_step_completed("transcode", "E01")
    manager1.save()

    manager2 = StateManager(clean_state_file)
    assert manager2.is_step_completed("transcode", "E01")

    manager2.mark_step_completed("transcode", "E02")
    manager2.save()

    manager3 = StateManager(clean_state_file)
    assert manager3.is_step_completed("transcode", "E01")
    assert manager3.is_step_completed("transcode", "E02")


def test_state_manager_create_progress_bar(clean_state_file):
    manager = StateManager(clean_state_file)

    progress = manager.create_progress_bar(10, "Test progress")

    assert progress is not None

    print("\n✓ Progress bar created successfully")
