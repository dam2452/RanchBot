import asyncio
import logging
from pathlib import Path
import sys
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest
import pytest_asyncio

mock_settings = MagicMock()
mock_settings.BOT_USERNAME = "test_bot"
mock_settings.FILE_SIZE_LIMIT_MB = 50
mock_settings.DEFAULT_RESOLUTION_KEY = "720p"
mock_settings.DEFAULT_SERIES = "ranczo"
mock_settings.EXTEND_BEFORE = 5
mock_settings.EXTEND_AFTER = 5
mock_settings.EXTEND_BEFORE_COMPILE = 1
mock_settings.EXTEND_AFTER_COMPILE = 1
mock_settings.MESSAGE_LIMIT = 5
mock_settings.LIMIT_DURATION = 30
mock_settings.MAX_CLIPS_PER_COMPILATION = 30
mock_settings.MAX_ADJUSTMENT_DURATION = 20
mock_settings.MAX_SEARCH_QUERY_LENGTH = 200
mock_settings.MAX_CLIP_DURATION = 60
mock_settings.MAX_CLIP_NAME_LENGTH = 40
mock_settings.MAX_REPORT_LENGTH = 1000
mock_settings.MAX_CLIPS_PER_USER = 100
mock_settings.LOG_LEVEL = "INFO"
mock_settings.ENVIRONMENT = "test"
mock_settings.VIDEO_DATA_DIR = "/tmp/test_videos"

sys.modules['bot.settings'] = MagicMock(settings=mock_settings)

from bot.database.db_provider import (  # pylint: disable=wrong-import-position
    reset_db,
    set_db,
)
from tests.integration.mocks.mock_database import MockDatabase  # pylint: disable=wrong-import-position
from tests.integration.mocks.mock_elasticsearch import MockElasticsearch  # pylint: disable=wrong-import-position
from tests.integration.mocks.mock_ffmpeg import MockFFmpeg  # pylint: disable=wrong-import-position


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

    def mock_scan_all_series():
        return ['ranczo']

    await MockDatabase.set_default_admin(
        user_id=123,
        username="TestUser",
        full_name="Test User",
        password="test_password",
    )
    logger.info("Mock admin 123 added")

    with patch('bot.services.reindex.series_scanner.SeriesScanner.scan_all_series', side_effect=mock_scan_all_series):
        yield MockDatabase

    reset_db()


@pytest_asyncio.fixture(scope="function", autouse=True)
def mock_es():
    MockElasticsearch.reset()

    async def mock_find_segment_by_quote(quote, segment_logger, series_name, size=1, **_kwargs):
        return await MockElasticsearch.find_segment_by_quote(quote, segment_logger, series_name, size)

    async def mock_get_season_details(_logger, series_name, **_kwargs):
        return await MockElasticsearch.get_season_details_from_elastic(_logger, series_name)

    async def mock_find_video_path_by_episode(season, episode_number, _logger, **_kwargs):
        return await MockElasticsearch.find_video_path_by_episode(season, episode_number, _logger)

    async def mock_find_segment_with_context(quote, _logger, series_name, context_size=15):
        return await MockElasticsearch.find_segment_with_context(quote, _logger, series_name, context_size)

    with patch('bot.search.transcription_finder.TranscriptionFinder.find_segment_by_quote', side_effect=mock_find_segment_by_quote), \
         patch('bot.search.transcription_finder.TranscriptionFinder.get_season_details_from_elastic', side_effect=mock_get_season_details), \
         patch('bot.search.transcription_finder.TranscriptionFinder.find_video_path_by_episode', side_effect=mock_find_video_path_by_episode), \
         patch('bot.search.transcription_finder.TranscriptionFinder.find_segment_with_context', side_effect=mock_find_segment_with_context):
        yield MockElasticsearch


@pytest_asyncio.fixture(scope="function", autouse=True)
def mock_ffmpeg():
    MockFFmpeg.reset()

    async def mock_extract_clip(video_path, start_time, end_time, clip_logger, output_path=None, resolution_key='720p'):
        return await MockFFmpeg.extract_clip(video_path, start_time, end_time, clip_logger, output_path, resolution_key)

    async def mock_get_video_duration(_video_path):
        return 5.0

    original_exists = Path.exists

    def mock_path_exists(self):
        if str(self).startswith('/fake/'):
            return True
        return original_exists(self)

    with patch('bot.video.clips_extractor.ClipsExtractor.extract_clip', side_effect=mock_extract_clip), \
         patch('bot.video.utils.get_video_duration', side_effect=mock_get_video_duration), \
         patch('bot.handlers.not_sending_videos.save_clip_handler.get_video_duration', side_effect=mock_get_video_duration), \
         patch('pathlib.Path.exists', mock_path_exists):
        yield MockFFmpeg
