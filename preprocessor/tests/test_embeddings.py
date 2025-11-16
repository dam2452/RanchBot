import json
from pathlib import Path
import sys

import pytest

from preprocessor.embedding_generator import EmbeddingGenerator

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TEST_VIDEO = Path(__file__).parent / "test_ranczo_S01E13.mp4"
TEST_VIDEO_DIR = Path(__file__).parent
TRANSCRIPTION_DIR = Path(__file__).parent / "output" / "transcriptions"
OUTPUT_DIR = Path(__file__).parent / "output" / "embeddings"


@pytest.mark.slow
def test_embeddings():
    assert TRANSCRIPTION_DIR.exists(), (
        f"Transcription directory not found: {TRANSCRIPTION_DIR}. "
        "Run test_transcription.py first!"
    )

    transcription_files = list(TRANSCRIPTION_DIR.glob("**/*.json"))
    assert len(transcription_files) > 0, (
        f"No transcription files found in {TRANSCRIPTION_DIR}. "
        "Run test_transcription.py first!"
    )

    generator = EmbeddingGenerator({
        "transcription_jsons": TRANSCRIPTION_DIR,
        "videos": TEST_VIDEO_DIR,
        "output_dir": OUTPUT_DIR,
        "model": "Alibaba-NLP/gme-Qwen2-VL-7B-Instruct",
        "segments_per_embedding": 5,
        "keyframe_strategy": "keyframes",
        "generate_text": True,
        "generate_video": True,
        "device": "cuda",
    })

    exit_code = generator.work()
    assert exit_code == 0, "Embedding generation failed"

    for trans_file in transcription_files:
        with open(trans_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        text_emb_count = len(data.get("text_embeddings", []))
        video_emb_count = len(data.get("video_embeddings", []))

        print(f"\n{trans_file.name}:")
        print(f"  - Text embeddings: {text_emb_count}")
        print(f"  - Video embeddings: {video_emb_count}")

        assert text_emb_count > 0 or video_emb_count > 0, (
            f"No embeddings generated for {trans_file.name}"
        )
