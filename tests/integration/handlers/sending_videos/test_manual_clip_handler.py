import logging

import pytest

from bot.handlers.sending_videos.manual_clip_handler import ManualClipHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestManualClipHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_manual_clip_success(self, mock_db, mock_es, mock_ffmpeg):
        mock_es.add_video_path(season=1, episode=1, video_path='/fake/s01e01.mp4')
        mock_ffmpeg.add_mock_clip('/fake/s01e01.mp4')

        message = self.create_message('/wytnij s01e01 1:00 2:00')
        responder = self.create_responder()

        handler = ManualClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video(), "Handler should send video"

    @pytest.mark.asyncio
    async def test_manual_clip_missing_arguments(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/cut s01e01')
        responder = self.create_responder()

        handler = ManualClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_manual_clip_invalid_episode_format(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/wytnij invalid 1:00 2:00')
        responder = self.create_responder()

        handler = ManualClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_manual_clip_invalid_time_format(self, mock_db, mock_es, mock_ffmpeg):
        mock_es.add_video_path(season=1, episode=1, video_path='/fake/s01e01.mp4')

        message = self.create_message('/wytnij s01e01 invalid 2:00')
        responder = self.create_responder()

        handler = ManualClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_manual_clip_end_before_start(self, mock_db, mock_es, mock_ffmpeg):
        mock_es.add_video_path(season=1, episode=1, video_path='/fake/s01e01.mp4')

        message = self.create_message('/cut s01e01 2:00 1:00')
        responder = self.create_responder()

        handler = ManualClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'wcześniej' in all_responses.lower() or 'earlier' in all_responses.lower() or 'przed' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_manual_clip_video_not_found(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/wytnij s99e99 1:00 2:00')
        responder = self.create_responder()

        handler = ManualClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_manual_clip_with_seconds(self, mock_db, mock_es, mock_ffmpeg):
        mock_es.add_video_path(season=1, episode=1, video_path='/fake/s01e01.mp4')
        mock_ffmpeg.add_mock_clip('/fake/s01e01.mp4')

        message = self.create_message('/wytnij s01e01 0:30 1:15')
        responder = self.create_responder()

        handler = ManualClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video() or responder.has_sent_text()

    @pytest.mark.asyncio
    async def test_manual_clip_different_aliases(self, mock_db, mock_es, mock_ffmpeg):
        mock_es.add_video_path(season=1, episode=1, video_path='/fake/s01e01.mp4')
        mock_ffmpeg.add_mock_clip('/fake/s01e01.mp4')

        for command in ['/wytnij', '/cut', '/wyt']:
            responder = self.create_responder()
            message = self.create_message(f'{command} s01e01 1:00 2:00')

            handler = ManualClipHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_video() or responder.has_sent_text(), f"Handler should respond to {command}"
