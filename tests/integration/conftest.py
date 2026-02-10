import asyncio
import logging
from unittest.mock import patch

import pytest
import pytest_asyncio


def pytest_collection_modifyitems(items):
    for item in items:
        if 'integration' in item.nodeid:
            item.add_marker(pytest.mark.integration)

from bot.database.database_manager import DatabaseManager
from bot.search.transcription_finder import TranscriptionFinder
from bot.video.clips_extractor import ClipsExtractor
from bot.video.clips_compiler import ClipsCompiler
from tests.e2e.settings import settings as s

from tests.integration.mocks.mock_elasticsearch import MockElasticsearch
from tests.integration.mocks.mock_ffmpeg import MockFFmpeg
from tests.integration.mocks.mock_database import MockDatabase

logger = logging.getLogger(__name__)
_test_lock = asyncio.Lock()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def db_pool():
    """Override E2E db_pool fixture - do nothing for integration tests"""
    yield None


@pytest_asyncio.fixture(scope="function", autouse=True)
async def test_client(db_pool):
    """Override E2E test_client fixture - do nothing for integration tests"""
    yield None


@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_database(db_pool):
    """Override E2E prepare_database fixture - do nothing for integration tests"""
    yield None


@pytest_asyncio.fixture(scope="function", autouse=True)
async def auth_token(test_client, prepare_database):
    """Override E2E auth_token fixture - do nothing for integration tests"""
    yield None


@pytest_asyncio.fixture(scope="function", autouse=True)
async def mock_db():
    MockDatabase.reset()

    original_methods = {}
    for method_name in dir(DatabaseManager):
        if not method_name.startswith('_'):
            method = getattr(DatabaseManager, method_name, None)
            if callable(method):
                original_methods[method_name] = method

    for method_name in dir(MockDatabase):
        if not method_name.startswith('_') and hasattr(DatabaseManager, method_name):
            mock_method = getattr(MockDatabase, method_name)
            setattr(DatabaseManager, method_name, mock_method)

    class MockTransaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class MockConnection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        def transaction(self):
            return MockTransaction()

        async def execute(self, *args, **kwargs):
            pass

        async def fetch(self, *args, **kwargs):
            return []

        async def fetchrow(self, *args, **kwargs):
            return None

        async def fetchval(self, *args, **kwargs):
            return None

    class MockPool:
        def is_closing(self):
            return False

        def acquire(self):
            return MockConnection()

    DatabaseManager.pool = MockPool()

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

    for method_name, original_method in original_methods.items():
        setattr(DatabaseManager, method_name, original_method)


@pytest_asyncio.fixture(scope="function")
def mock_es():
    MockElasticsearch.reset()

    original_find = TranscriptionFinder.find_segment_by_quote
    original_season = TranscriptionFinder.get_season_details_from_elastic

    async def mock_find_segment_by_quote(quote, logger, series_name, size=1):
        return await MockElasticsearch.find_segment_by_quote(quote, logger, series_name, size)

    async def mock_get_season_details(logger, series_name):
        return await MockElasticsearch.get_season_details_from_elastic(logger, series_name)

    with patch.object(TranscriptionFinder, 'find_segment_by_quote', side_effect=mock_find_segment_by_quote), \
         patch.object(TranscriptionFinder, 'get_season_details_from_elastic', side_effect=mock_get_season_details):
        yield MockElasticsearch

    TranscriptionFinder.find_segment_by_quote = original_find
    TranscriptionFinder.get_season_details_from_elastic = original_season


@pytest_asyncio.fixture(scope="function")
def mock_ffmpeg():
    MockFFmpeg.reset()

    original_extract = ClipsExtractor.extract_clip

    async def mock_extract_clip(video_path, start_time, end_time, logger, output_path=None, resolution_key='720p'):
        return await MockFFmpeg.extract_clip(video_path, start_time, end_time, logger, output_path, resolution_key)

    with patch.object(ClipsExtractor, 'extract_clip', side_effect=mock_extract_clip):
        yield MockFFmpeg

    ClipsExtractor.extract_clip = original_extract
