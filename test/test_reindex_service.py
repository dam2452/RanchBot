import logging

import pytest

from bot.services.reindex.reindex_service import ReindexService


@pytest.fixture
def logger():
    return logging.getLogger("test")


@pytest.mark.asyncio
async def test_reindex_single_series(logger): # pylint: disable=redefined-outer-name
    pytest.skip("Integration test - requires Elasticsearch")
    service = ReindexService(logger)

    progress_messages = []

    async def progress_callback(msg, cur, tot): # pylint: disable=unused-argument
        progress_messages.append(msg)

    result = await service.reindex_series("ranczo", progress_callback)

    assert result.series_name == "ranczo"
    assert result.episodes_processed > 0
    assert result.documents_indexed > 0
    assert len(progress_messages) > 0


@pytest.mark.asyncio
async def test_reindex_invalid_series(logger): # pylint: disable=redefined-outer-name
    service = ReindexService(logger)

    async def progress_callback(msg, cur, tot): # pylint: disable=unused-argument
        pass

    with pytest.raises(ValueError, match="No zip files found"):
        await service.reindex_series("nonexistent_series", progress_callback)


@pytest.mark.asyncio
async def test_reindex_all_new(logger): # pylint: disable=redefined-outer-name
    pytest.skip("Integration test - requires Elasticsearch")
    service = ReindexService(logger)

    async def progress_callback(msg, cur, tot): # pylint: disable=unused-argument
        pass

    results = await service.reindex_all_new(progress_callback)

    assert isinstance(results, list)
