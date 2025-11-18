from pathlib import Path
import sys

import pytest

from preprocessor.processing.elastic_search_indexer import ElasticSearchIndexer
from preprocessor.tests.conftest import require_transcription_files

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TRANSCRIPTION_DIR = Path(__file__).parent / "output" / "transcriptions"
INDEX_NAME = "test_ranczo"


@pytest.mark.elasticsearch
def test_indexer():
    require_transcription_files()

    indexer = ElasticSearchIndexer({
        "name": INDEX_NAME,
        "transcription_jsons": TRANSCRIPTION_DIR,
        "dry_run": False,
        "append": False,
    })

    exit_code = indexer.work()
    assert exit_code == 0, "Elasticsearch indexing failed"

    print(f"\n✓ Index '{INDEX_NAME}' created/updated in Elasticsearch")
