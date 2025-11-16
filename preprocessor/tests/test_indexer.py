from pathlib import Path
import sys

import pytest

from preprocessor.elastic_search_indexer import ElasticSearchIndexer

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TRANSCRIPTION_DIR = Path(__file__).parent / "output" / "transcriptions"
INDEX_NAME = "test_ranczo"


@pytest.mark.elasticsearch
def test_indexer():
    assert TRANSCRIPTION_DIR.exists(), (
        f"Transcription directory not found: {TRANSCRIPTION_DIR}. "
        "Run test_transcription.py first!"
    )

    transcription_files = list(TRANSCRIPTION_DIR.glob("**/*.json"))
    assert len(transcription_files) > 0, (
        f"No transcription files found in {TRANSCRIPTION_DIR}. "
        "Run test_transcription.py first!"
    )

    indexer = ElasticSearchIndexer({
        "name": INDEX_NAME,
        "transcription_jsons": TRANSCRIPTION_DIR,
        "dry_run": False,
        "append": False,
    })

    exit_code = indexer.work()
    assert exit_code == 0, "Elasticsearch indexing failed"

    print(f"\n✓ Index '{INDEX_NAME}' created/updated in Elasticsearch")
