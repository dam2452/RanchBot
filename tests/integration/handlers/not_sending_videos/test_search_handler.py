import logging

import pytest

from bot.handlers.not_sending_videos.search_handler import SearchHandler
from tests.integration.base_integration_test import (
    BaseIntegrationTest,
    FakeMessage,
    FakeResponder,
)
from tests.integration.mocks.test_data import TestSegments

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestSearchHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_search_existing_quote_returns_results(self, mock_es, mock_ffmpeg):
        segment = TestSegments.get_geniusz_segment()
        ep_info = segment.pop('episode_info')
        segment.pop('_quote_keywords', None)
        mock_es.add_segment(
            **segment,
            season=ep_info['season'],
            episode_number=ep_info['episode_number'],
            episode_title=ep_info['title'],
            quote_keywords=['geniusz'],
        )

        message = self.create_message('/szukaj geniusz')
        responder = self.create_responder()

        handler = SearchHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send search results"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'geniusz' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_search_nonexistent_quote_returns_no_results(self, mock_es, mock_ffmpeg):
        message = self.create_message('/szukaj nieistniejący_cytat')
        responder = self.create_responder()

        handler = SearchHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send response"

    @pytest.mark.asyncio
    async def test_search_without_arguments_returns_validation_error(self, mock_es, mock_ffmpeg):
        message = self.create_message('/szukaj')
        responder = self.create_responder()

        handler = SearchHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send validation error"
