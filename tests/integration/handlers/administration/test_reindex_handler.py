import logging
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest

from bot.handlers.administration.reindex_handler import ReindexHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class MockReindexResult:
    def __init__(self, series_name='ranczo', documents_indexed=100, episodes_processed=10):
        self.series_name = series_name
        self.documents_indexed = documents_indexed
        self.episodes_processed = episodes_processed


@pytest.mark.usefixtures("mock_db")
class TestReindexHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_reindex_missing_argument(self, mock_db):
        message = self.create_message('/reindex')
        responder = self.create_responder()

        handler = ReindexHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'użyj' in all_responses.lower() or 'usage' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_reindex_invalid_target_format(self, mock_db):
        message = self.create_message('/reindex invalid@#$%')
        responder = self.create_responder()

        handler = ReindexHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_reindex_valid_series_name(self, mock_db):
        message = self.create_message('/ridx ranczo')
        responder = self.create_responder()

        with patch('bot.handlers.administration.reindex_handler.ReindexService') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.reindex_series = AsyncMock(return_value=MockReindexResult())
            mock_service.return_value = mock_instance

            handler = ReindexHandler(message, responder, logger)
            await handler.handle()

        assert responder.has_sent_text(), "Handler should send response"

    @pytest.mark.asyncio
    async def test_reindex_all_command(self, mock_db):
        message = self.create_message('/reindex all')
        responder = self.create_responder()

        with patch('bot.handlers.administration.reindex_handler.ReindexService') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.reindex_all = AsyncMock(return_value=[
                MockReindexResult('series1', 100, 10),
                MockReindexResult('series2', 200, 20),
            ])
            mock_service.return_value = mock_instance

            handler = ReindexHandler(message, responder, logger)
            await handler.handle()

        assert responder.has_sent_text(), "Handler should send response"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '300' in all_responses or '30' in all_responses

    @pytest.mark.asyncio
    async def test_reindex_all_new_command(self, mock_db):
        message = self.create_message('/reindeksuj all-new')
        responder = self.create_responder()

        with patch('bot.handlers.administration.reindex_handler.ReindexService') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.reindex_all_new = AsyncMock(return_value=[
                MockReindexResult('new_series', 50, 5),
            ])
            mock_service.return_value = mock_instance

            handler = ReindexHandler(message, responder, logger)
            await handler.handle()

        assert responder.has_sent_text(), "Handler should send response"

    @pytest.mark.asyncio
    async def test_reindex_all_new_no_new_series(self, mock_db):
        message = self.create_message('/reindex all-new')
        responder = self.create_responder()

        with patch('bot.handlers.administration.reindex_handler.ReindexService') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.reindex_all_new = AsyncMock(return_value=[])
            mock_service.return_value = mock_instance

            handler = ReindexHandler(message, responder, logger)
            await handler.handle()

        assert responder.has_sent_text(), "Handler should send message about no new series"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'brak' in all_responses.lower() or 'no' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_reindex_with_exception(self, mock_db):
        message = self.create_message('/reindex ranczo')
        responder = self.create_responder()

        with patch('bot.handlers.administration.reindex_handler.ReindexService') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.reindex_series = AsyncMock(side_effect=Exception('Test error'))
            mock_service.return_value = mock_instance

            handler = ReindexHandler(message, responder, logger)
            await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'błąd' in all_responses.lower() or 'error' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_reindex_accepts_underscores_and_hyphens(self, mock_db):
        message = self.create_message('/reindex test_series-name')
        responder = self.create_responder()

        with patch('bot.handlers.administration.reindex_handler.ReindexService') as mock_service:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.reindex_series = AsyncMock(return_value=MockReindexResult())
            mock_service.return_value = mock_instance

            handler = ReindexHandler(message, responder, logger)
            await handler.handle()

        assert responder.has_sent_text(), "Handler should accept series name with underscores and hyphens"
