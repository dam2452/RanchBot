import logging

import pytest

from bot.handlers.sending_videos.inline_clip_handler import InlineClipHandler
from tests.integration.base_integration_test import BaseIntegrationTest
from tests.integration.mocks.test_data import TestSegments

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestInlineClipHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_inline_clip_with_saved_clip(self, mock_db, mock_es, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'test_clip', b'fake_video', 0.0, 5.0, 5.0)
        mock_ffmpeg.add_mock_clip_from_bytes(b'fake_video')

        message = self.create_message('/inline test_clip', user_id=user_id)
        responder = self.create_responder()

        handler = InlineClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text() or len(responder.documents) > 0

    @pytest.mark.asyncio
    async def test_inline_clip_with_search_results(self, mock_db, mock_es, mock_ffmpeg):
        segment = TestSegments.get_geniusz_segment()
        ep_info = segment.pop('episode_info')
        segment.pop('_quote_keywords', None)
        mock_es.add_segment(
            **segment,
            season=ep_info['season'],
            episode_number=ep_info['episode_number'],
            episode_title=ep_info['title'],
            quote_keywords=['test'],
        )
        mock_ffmpeg.add_mock_clip(segment['video_path'])

        message = self.create_message('/inline test', user_id=self.admin_id)
        responder = self.create_responder()

        handler = InlineClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text() or len(responder.documents) > 0

    @pytest.mark.asyncio
    async def test_inline_clip_no_results(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/inline nonexistent_query')
        responder = self.create_responder()

        handler = InlineClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'nie' in all_responses.lower() or 'no' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_inline_clip_missing_argument(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/inline')
        responder = self.create_responder()

        handler = InlineClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_inline_clip_with_multiple_words(self, mock_db, mock_es, mock_ffmpeg):
        segment = TestSegments.get_geniusz_segment()
        ep_info = segment.pop('episode_info')
        segment.pop('_quote_keywords', None)
        mock_es.add_segment(
            **segment,
            season=ep_info['season'],
            episode_number=ep_info['episode_number'],
            episode_title=ep_info['title'],
            quote_keywords=['wielki', 'geniusz'],
        )
        mock_ffmpeg.add_mock_clip(segment['video_path'])

        message = self.create_message('/inline wielki geniusz')
        responder = self.create_responder()

        handler = InlineClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text() or len(responder.documents) > 0

    @pytest.mark.asyncio
    async def test_inline_clip_combined_saved_and_search(self, mock_db, mock_es, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'combo', b'saved_data', 0.0, 5.0, 5.0)

        segment = TestSegments.get_geniusz_segment()
        ep_info = segment.pop('episode_info')
        segment.pop('_quote_keywords', None)
        mock_es.add_segment(
            **segment,
            season=ep_info['season'],
            episode_number=ep_info['episode_number'],
            episode_title=ep_info['title'],
            quote_keywords=['combo'],
        )
        mock_ffmpeg.add_mock_clip_from_bytes(b'saved_data')
        mock_ffmpeg.add_mock_clip(segment['video_path'])

        message = self.create_message('/inline combo', user_id=user_id)
        responder = self.create_responder()

        handler = InlineClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text() or len(responder.documents) > 0
