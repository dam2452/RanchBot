import logging
from pathlib import Path

import pytest

from bot.services.reindex.zip_extractor import ZipExtractor


@pytest.fixture
def logger():
    return logging.getLogger("test")


@pytest.fixture
def sample_zip():
    return Path("preprocessor/output_data/archives/S00/E01/ranczo_S00E01_elastic_documents.zip")


def test_extract_zip_to_memory(logger, sample_zip): # pylint: disable=redefined-outer-name
    if not sample_zip.exists():
        pytest.skip("Sample zip not found")

    extractor = ZipExtractor(logger)
    files = extractor.extract_to_memory(sample_zip)

    assert "text_segments" in files
    assert "text_embeddings" in files
    assert "video_frames" in files
    assert "episode_names" in files


def test_parse_jsonl_from_memory(logger, sample_zip): # pylint: disable=redefined-outer-name
    if not sample_zip.exists():
        pytest.skip("Sample zip not found")

    extractor = ZipExtractor(logger)
    files = extractor.extract_to_memory(sample_zip)

    documents = extractor.parse_jsonl_from_memory(files["text_segments"])

    assert len(documents) > 0
    assert "episode_id" in documents[0]
    assert "text" in documents[0]
    assert "video_path" in documents[0]


def test_corrupted_zip(logger, tmp_path): # pylint: disable=redefined-outer-name
    corrupted_zip = tmp_path / "corrupted.zip"
    corrupted_zip.write_text("not a zip file")

    extractor = ZipExtractor(logger)

    with pytest.raises(ValueError, match="Invalid zip file"):
        extractor.extract_to_memory(corrupted_zip)
