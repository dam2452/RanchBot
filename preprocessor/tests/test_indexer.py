from pathlib import Path
import sys

import pytest

from preprocessor.processing.elastic_search_indexer import ElasticSearchIndexer
from preprocessor.tests.conftest import require_transcription_files

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TRANSCRIPTION_DIR = Path(__file__).parent / "output" / "transcriptions" / "json"
INDEX_NAME = "test_ranczo"


@pytest.mark.elasticsearch
@pytest.mark.asyncio
async def test_indexer_create_new_index():
    require_transcription_files()

    indexer = ElasticSearchIndexer({
        "name": INDEX_NAME,
        "transcription_jsons": TRANSCRIPTION_DIR,
        "dry_run": False,
        "append": False,
        "series_name": "test_ranczo",
        "state_manager": None,
    })

    exit_code = indexer.work()
    assert exit_code == 0, "Elasticsearch indexing failed"

    print(f"\n✓ Index '{INDEX_NAME}' created/updated in Elasticsearch")


@pytest.mark.elasticsearch
@pytest.mark.asyncio
async def test_indexer_append_mode():
    require_transcription_files()

    indexer = ElasticSearchIndexer({
        "name": INDEX_NAME,
        "transcription_jsons": TRANSCRIPTION_DIR,
        "dry_run": False,
        "append": True,
        "series_name": "test_ranczo",
        "state_manager": None,
    })

    exit_code = indexer.work()
    assert exit_code == 0, "Elasticsearch indexing in append mode failed"

    print(f"\n✓ Index '{INDEX_NAME}' appended in Elasticsearch")


@pytest.mark.elasticsearch
def test_indexer_dry_run():
    require_transcription_files()

    indexer = ElasticSearchIndexer({
        "name": INDEX_NAME,
        "transcription_jsons": TRANSCRIPTION_DIR,
        "dry_run": True,
        "append": False,
        "series_name": "test_ranczo",
        "state_manager": None,
    })

    exit_code = indexer.work()
    assert exit_code == 0, "Elasticsearch dry-run indexing failed"

    print(f"\n✓ Dry-run completed for index '{INDEX_NAME}'")
