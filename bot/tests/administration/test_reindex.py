from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import bot.responses.administration.reindex_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestReindexHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_reindex_without_args(self):
        response = self.send_command('/reindex')
        self.assert_response_contains(response, [msg.get_reindex_usage_message()])

    @pytest.mark.asyncio
    @patch('bot.handlers.administration.reindex_handler.ReindexService')
    async def test_reindex_specific_series(self, mock_service_class):
        mock_service = MagicMock()
        mock_service.reindex_series = AsyncMock()
        mock_service.close = AsyncMock()
        mock_result = MagicMock()
        mock_result.series_name = "ranczo"
        mock_result.episodes_processed = 10
        mock_result.documents_indexed = 100
        mock_result.errors = []
        mock_service.reindex_series.return_value = mock_result
        mock_service_class.return_value = mock_service

        response = self.send_command('/reindex ranczo')
        self.assert_response_contains(response, [msg.get_reindex_started_message("ranczo")])

    @pytest.mark.asyncio
    @patch('bot.handlers.administration.reindex_handler.ReindexService')
    async def test_reindex_all(self, mock_service_class):
        mock_service = MagicMock()
        mock_service.reindex_all = AsyncMock()
        mock_service.close = AsyncMock()
        mock_result = MagicMock()
        mock_result.documents_indexed = 100
        mock_result.episodes_processed = 10
        mock_service.reindex_all.return_value = [mock_result]
        mock_service_class.return_value = mock_service

        response = self.send_command('/reindex all')
        self.assert_response_contains(response, [msg.get_reindex_started_message("all")])

    @pytest.mark.asyncio
    @patch('bot.handlers.administration.reindex_handler.ReindexService')
    async def test_reindex_all_new(self, mock_service_class):
        mock_service = MagicMock()
        mock_service.reindex_all_new = AsyncMock()
        mock_service.close = AsyncMock()
        mock_result = MagicMock()
        mock_result.documents_indexed = 100
        mock_result.episodes_processed = 10
        mock_service.reindex_all_new.return_value = [mock_result]
        mock_service_class.return_value = mock_service

        response = self.send_command('/reindex all-new')
        self.assert_response_contains(response, [msg.get_reindex_started_message("all-new")])

    @pytest.mark.asyncio
    @patch('bot.handlers.administration.reindex_handler.ReindexService')
    async def test_reindex_short_alias(self, mock_service_class):
        mock_service = MagicMock()
        mock_service.reindex_series = AsyncMock()
        mock_service.close = AsyncMock()
        mock_result = MagicMock()
        mock_result.series_name = "ranczo"
        mock_result.episodes_processed = 10
        mock_result.documents_indexed = 100
        mock_result.errors = []
        mock_service.reindex_series.return_value = mock_result
        mock_service_class.return_value = mock_service

        response = self.send_command('/rei ranczo')
        self.assert_response_contains(response, [msg.get_reindex_started_message("ranczo")])
