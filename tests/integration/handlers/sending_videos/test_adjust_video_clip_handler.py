import json
import logging

import pytest

from bot.database.models import ClipType
from bot.handlers.sending_videos.adjust_video_clip_handler import AdjustVideoClipHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestAdjustVideoClipHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_adjust_clip_relative_success(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {
            'video_path': '/fake/path.mp4',
            'start_time': 10.0,
            'end_time': 20.0,
            'episode_info': {'season': 1, 'episode_number': 1},
        }

        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        message = self.create_message('/dostosuj 1 2 3', user_id=chat_id)
        responder = self.create_responder()

        handler = AdjustVideoClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video() or responder.has_sent_text()

    @pytest.mark.asyncio
    async def test_adjust_clip_absolute_success(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {
            'video_path': '/fake/path.mp4',
            'start_time': 10.0,
            'end_time': 20.0,
            'episode_info': {'season': 1, 'episode_number': 1},
        }

        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        message = self.create_message('/adostosuj 1 2 3', user_id=chat_id)
        responder = self.create_responder()

        handler = AdjustVideoClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video() or responder.has_sent_text()

    @pytest.mark.asyncio
    async def test_adjust_clip_no_previous_search(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/adjust 1 2 3')
        responder = self.create_responder()

        handler = AdjustVideoClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_adjust_clip_missing_arguments(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/dostosuj 1')
        responder = self.create_responder()

        handler = AdjustVideoClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_adjust_clip_invalid_segment_index(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))

        message = self.create_message('/dostosuj 99 2 3', user_id=chat_id)
        responder = self.create_responder()

        handler = AdjustVideoClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_adjust_clip_invalid_time_format(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))

        message = self.create_message('/dostosuj 1 abc def', user_id=chat_id)
        responder = self.create_responder()

        handler = AdjustVideoClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_adjust_clip_invalid_interval(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        message = self.create_message('/dostosuj 1 100 0', user_id=chat_id)
        responder = self.create_responder()

        handler = AdjustVideoClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_adjust_clip_different_aliases(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        for command in ['/dostosuj', '/adjust', '/d', '/adostosuj', '/aadjust', '/ad']:
            await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))
            responder = self.create_responder()
            message = self.create_message(f'{command} 1 2 3', user_id=chat_id)

            handler = AdjustVideoClipHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_video() or responder.has_sent_text(), f"Handler should respond to {command}"
