import pytest
import logging

from tests.integration.base_integration_test import BaseIntegrationTest, FakeMessage, FakeResponder
from tests.integration.mocks.test_data import TestSegments
from bot.handlers.sending_videos.clip_handler import ClipHandler

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestClipHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_clip_found_returns_video(self, mock_es, mock_ffmpeg):
        segment = TestSegments.get_geniusz_segment()
        ep_info = segment.pop('episode_info')
        segment.pop('_quote_keywords', None)
        mock_es.add_segment(
            **segment,
            season=ep_info['season'],
            episode_number=ep_info['episode_number'],
            episode_title=ep_info['title'],
            quote_keywords=['geniusz']
        )
        mock_ffmpeg.add_mock_clip(segment['video_path'])

        message = self.create_message('/klip geniusz')
        responder = self.create_responder()

        handler = ClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video(), "Handler should send video"
        assert len(responder.videos) == 1

    @pytest.mark.asyncio
    async def test_clip_not_found_returns_error_message(self, mock_es, mock_ffmpeg):
        message = self.create_message('/klip nieistniejący_cytat')
        responder = self.create_responder()

        handler = ClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        assert not responder.has_sent_video(), "Handler should not send video"

    @pytest.mark.asyncio
    async def test_no_quote_provided_returns_validation_error(self, mock_es, mock_ffmpeg):
        message = self.create_message('/klip')
        responder = self.create_responder()

        handler = ClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send validation error"
