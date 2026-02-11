import logging

import pytest

from bot.handlers.not_sending_videos.transcription_handler import TranscriptionHandler
from tests.integration.base_integration_test import BaseIntegrationTest
from tests.integration.mocks.test_data import TestSegments

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestTranscriptionHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_transcription_found(self, mock_db, mock_es, mock_ffmpeg):
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

        message = self.create_message('/transkrypcja geniusz')
        responder = self.create_responder()

        handler = TranscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send transcription"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'geniusz' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_transcription_not_found(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/transcription nonexistent_quote')
        responder = self.create_responder()

        handler = TranscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'nie' in all_responses.lower() or 'no' in all_responses.lower() or 'brak' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_transcription_missing_argument(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/t')
        responder = self.create_responder()

        handler = TranscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_transcription_with_multiple_words(self, mock_db, mock_es, mock_ffmpeg):
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

        message = self.create_message('/transkrypcja wielki geniusz')
        responder = self.create_responder()

        handler = TranscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send transcription"

    @pytest.mark.asyncio
    async def test_transcription_different_aliases(self, mock_db, mock_es, mock_ffmpeg):
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

        for command in ['/transkrypcja', '/transcription', '/t']:
            responder = self.create_responder()
            message = self.create_message(f'{command} test')

            handler = TranscriptionHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to {command}"
