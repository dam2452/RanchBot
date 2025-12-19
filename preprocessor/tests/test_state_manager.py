import json
from pathlib import Path
import sys

import pytest

from preprocessor.core.state_manager import StateManager

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# pylint: disable=redefined-outer-name,protected-access

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
    manager = StateManager(series_name="test", working_dir=clean_state_file.parent)

    assert manager._StateManager__state_file == clean_state_file
    assert not clean_state_file.exists(), "State file should not exist before save"


def test_state_manager_mark_step_completed(clean_state_file):
    manager = StateManager(series_name="test", working_dir=clean_state_file.parent)
    manager.load_or_create_state()

    assert not manager.is_step_completed("transcode", "E01")

    manager.mark_step_started("transcode", "E01")
    assert not manager.is_step_completed("transcode", "E01")

    manager.mark_step_completed("transcode", "E01")
    assert manager.is_step_completed("transcode", "E01")


def test_state_manager_multiple_steps(clean_state_file):
    manager = StateManager(series_name="test", working_dir=clean_state_file.parent)
    manager.load_or_create_state()

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
    manager1 = StateManager(series_name="test", working_dir=clean_state_file.parent)
    manager1.load_or_create_state()

    manager1.mark_step_completed("transcode", "E01")
    manager1.mark_step_completed("transcription", "E02")
    manager1.save_state()

    assert clean_state_file.exists(), "State file should exist after save"

    manager2 = StateManager(series_name="test", working_dir=clean_state_file.parent)
    manager2.load_or_create_state()

    assert manager2.is_step_completed("transcode", "E01")
    assert manager2.is_step_completed("transcription", "E02")
    assert not manager2.is_step_completed("embeddings", "E03")


def test_state_manager_persistence(clean_state_file):
    manager1 = StateManager(series_name="test", working_dir=clean_state_file.parent)
    manager1.load_or_create_state()
    manager1.mark_step_completed("transcode", "E01")
    manager1.mark_step_completed("transcode", "E02")
    manager1.save_state()

    with open(clean_state_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "completed_steps" in data
    steps = {(s["step"], s["episode"]) for s in data["completed_steps"]}
    assert ("transcode", "E01") in steps
    assert ("transcode", "E02") in steps


def test_state_manager_overwrite_protection(clean_state_file):
    manager = StateManager(series_name="test", working_dir=clean_state_file.parent)
    manager.load_or_create_state()

    manager.mark_step_completed("transcode", "E01")
    assert manager.is_step_completed("transcode", "E01")

    manager.mark_step_started("transcode", "E01")
    assert manager.is_step_completed("transcode", "E01"), "Completed status should not be overwritten by started"


def test_state_manager_multiple_instances(clean_state_file):
    manager1 = StateManager(series_name="test", working_dir=clean_state_file.parent)
    manager1.load_or_create_state()
    manager1.mark_step_completed("transcode", "E01")
    manager1.save_state()

    manager2 = StateManager(series_name="test", working_dir=clean_state_file.parent)
    manager2.load_or_create_state()
    assert manager2.is_step_completed("transcode", "E01")

    manager2.mark_step_completed("transcode", "E02")
    manager2.save_state()

    manager3 = StateManager(series_name="test", working_dir=clean_state_file.parent)
    manager3.load_or_create_state()
    assert manager3.is_step_completed("transcode", "E01")
    assert manager3.is_step_completed("transcode", "E02")


def test_state_manager_create_progress_bar(clean_state_file):
    manager = StateManager(series_name="test", working_dir=clean_state_file.parent)

    progress = manager.create_progress_bar(10, "Test progress")

    assert progress is not None

    print("\n✓ Progress bar created successfully")
