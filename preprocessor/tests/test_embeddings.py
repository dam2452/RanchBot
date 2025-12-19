import json
from pathlib import Path
import sys

import pytest

from preprocessor.processing.embedding_generator import EmbeddingGenerator
from preprocessor.tests.conftest import require_transcription_files

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_ranczo_S01E13.mp4"
TEST_VIDEO_DIR = Path(__file__).parent
TRANSCRIPTION_DIR = Path(__file__).parent / "output" / "transcriptions"
OUTPUT_DIR = Path(__file__).parent / "output" / "embeddings"
SCENE_TIMESTAMPS_DIR = Path(__file__).parent / "output" / "scene_timestamps"


@pytest.mark.slow
@pytest.mark.embeddings
def test_text_embeddings():
    transcription_files = require_transcription_files()

    generator = EmbeddingGenerator({
        "transcription_jsons": TRANSCRIPTION_DIR,
        "videos": None,
        "output_dir": OUTPUT_DIR,
        "model": "Alibaba-NLP/gme-Qwen2-VL-7B-Instruct",
        "segments_per_embedding": 5,
        "keyframe_strategy": "keyframes",
        "generate_text": True,
        "generate_video": False,
        "device": "cuda",
        "max_workers": 1,
        "batch_size": 24,
    })

    exit_code = generator.work()
    assert exit_code == 0, "Text embedding generation failed"

    for trans_file in transcription_files:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        text_emb_count = len(data.get("text_embeddings", []))

        print(f"\n{trans_file.name}:")
        print(f"  - Text embeddings: {text_emb_count}")

        assert text_emb_count > 0, f"No text embeddings generated for {trans_file.name}"

        for emb in data["text_embeddings"]:
            assert "segment_range" in emb, "Missing 'segment_range' in text embedding"
            assert "text" in emb, "Missing 'text' in text embedding"
            assert "embedding" in emb, "Missing 'embedding' in text embedding"
            assert len(emb["embedding"]) > 0, "Empty embedding vector"


@pytest.mark.slow
@pytest.mark.embeddings
def test_video_embeddings_keyframes():
    transcription_files = require_transcription_files()

    generator = EmbeddingGenerator({
        "transcription_jsons": TRANSCRIPTION_DIR,
        "videos": TEST_VIDEO_DIR,
        "output_dir": OUTPUT_DIR,
        "model": "Alibaba-NLP/gme-Qwen2-VL-7B-Instruct",
        "segments_per_embedding": 5,
        "keyframe_strategy": "keyframes",
        "keyframe_interval": 4,
        "generate_text": False,
        "generate_video": True,
        "device": "cuda",
        "max_workers": 1,
        "batch_size": 24,
    })

    exit_code = generator.work()
    assert exit_code == 0, "Video embedding generation failed"

    for trans_file in transcription_files:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        video_emb_count = len(data.get("video_embeddings", []))

        print(f"\n{trans_file.name}:")
        print(f"  - Video embeddings: {video_emb_count}")

        assert video_emb_count > 0, f"No video embeddings generated for {trans_file.name}"

        for emb in data["video_embeddings"]:
            assert "frame_number" in emb, "Missing 'frame_number' in video embedding"
            assert "timestamp" in emb, "Missing 'timestamp' in video embedding"
            assert "type" in emb, "Missing 'type' in video embedding"
            assert "embedding" in emb, "Missing 'embedding' in video embedding"
            assert len(emb["embedding"]) > 0, "Empty embedding vector"
            assert emb["type"] == "keyframe", f"Unexpected embedding type: {emb['type']}"


@pytest.mark.slow
@pytest.mark.embeddings
def test_video_embeddings_scene_changes():
    transcription_files = require_transcription_files()

    if not SCENE_TIMESTAMPS_DIR.exists() or not list(SCENE_TIMESTAMPS_DIR.glob("*.json")):
        pytest.skip("Scene timestamps not found. Run test_scene_detection.py first!")

    generator = EmbeddingGenerator({
        "transcription_jsons": TRANSCRIPTION_DIR,
        "videos": TEST_VIDEO_DIR,
        "output_dir": OUTPUT_DIR,
        "model": "Alibaba-NLP/gme-Qwen2-VL-7B-Instruct",
        "segments_per_embedding": 5,
        "keyframe_strategy": "scene_changes",
        "keyframe_interval": 1,
        "generate_text": False,
        "generate_video": True,
        "device": "cuda",
        "max_workers": 1,
        "batch_size": 24,
        "scene_timestamps_dir": SCENE_TIMESTAMPS_DIR,
    })

    exit_code = generator.work()
    assert exit_code == 0, "Scene-based video embedding generation failed"

    for trans_file in transcription_files:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        video_emb_count = len(data.get("video_embeddings", []))

        print(f"\n{trans_file.name}:")
        print(f"  - Video embeddings (scene-based): {video_emb_count}")

        assert video_emb_count > 0, f"No video embeddings generated for {trans_file.name}"

        for emb in data["video_embeddings"]:
            assert "frame_number" in emb, "Missing 'frame_number' in video embedding"
            assert "timestamp" in emb, "Missing 'timestamp' in video embedding"
            assert "type" in emb, "Missing 'type' in video embedding"
            assert "scene_number" in emb, "Missing 'scene_number' in video embedding"
            assert "embedding" in emb, "Missing 'embedding' in video embedding"
            assert len(emb["embedding"]) > 0, "Empty embedding vector"
            assert emb["type"] in {"scene_start", "scene_mid", "scene_end"}, \
                f"Unexpected embedding type: {emb['type']}"
