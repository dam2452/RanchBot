import asyncio
import logging
from unittest.mock import patch

import pytest
import pytest_asyncio

from bot.database.db_provider import set_db, reset_db
from tests.e2e.settings import settings as s
from tests.integration.mocks.mock_database import MockDatabase
from tests.integration.mocks.mock_elasticsearch import MockElasticsearch
from tests.integration.mocks.mock_ffmpeg import MockFFmpeg


def pytest_collection_modifyitems(items):
    for item in items:
        if 'integration' in item.nodeid:
            item.add_marker(pytest.mark.integration)

logger = logging.getLogger(__name__)
_test_lock = asyncio.Lock()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def db_pool():
    """Override E2E db_pool fixture - do nothing for integration tests"""
    yield None


@pytest_asyncio.fixture(scope="function", autouse=True)
async def test_client():
    """Override E2E test_client fixture - do nothing for integration tests"""
    yield None


@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_database():
    """Override E2E prepare_database fixture - do nothing for integration tests"""
    yield None


@pytest_asyncio.fixture(scope="function", autouse=True)
async def auth_token():
    """Override E2E auth_token fixture - do nothing for integration tests"""
    yield None


@pytest_asyncio.fixture(scope="function", autouse=True)
async def mock_db():
    MockDatabase.reset()
    set_db(MockDatabase)

    i = 0
    for admin_id in s.TEST_ADMINS.split(","):
        await MockDatabase.set_default_admin(
            user_id=int(admin_id),
            username=f"TestUser{i}",
            full_name=f"TestUser{i}",
            password=s.TEST_PASSWORD.get_secret_value(),
        )
        logger.info(f"Mock admin {admin_id} added")
        i += 1

    yield MockDatabase

    reset_db()


@pytest_asyncio.fixture(scope="function", autouse=True)
def mock_es():
    MockElasticsearch.reset()

    async def mock_find_segment_by_quote(quote, segment_logger, series_name, size=1):
        return await MockElasticsearch.find_segment_by_quote(quote, segment_logger, series_name, size)

    async def mock_get_season_details(season_logger, series_name):
        return await MockElasticsearch.get_season_details_from_elastic(season_logger, series_name)

    with patch('bot.search.transcription_finder.TranscriptionFinder.find_segment_by_quote', side_effect=mock_find_segment_by_quote), \
         patch('bot.search.transcription_finder.TranscriptionFinder.get_season_details_from_elastic', side_effect=mock_get_season_details):
        yield MockElasticsearch


@pytest_asyncio.fixture(scope="function", autouse=True)
def mock_ffmpeg():
    MockFFmpeg.reset()

    async def mock_extract_clip(video_path, start_time, end_time, clip_logger, output_path=None, resolution_key='720p'):
        return await MockFFmpeg.extract_clip(video_path, start_time, end_time, clip_logger, output_path, resolution_key)

    with patch('bot.video.clips_extractor.ClipsExtractor.extract_clip', side_effect=mock_extract_clip):
        yield MockFFmpeg
