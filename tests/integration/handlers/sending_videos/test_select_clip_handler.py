import json
import logging

import pytest

from bot.handlers.sending_videos.select_clip_handler import SelectClipHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestSelectClipHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_select_clip_success(self, mock_db, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {
            'id': '123',
            'video_path': '/fake/path.mp4',
            'start_time': 10.0,
            'end_time': 20.0,
        }
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        message = self.create_message('/wybierz 1', user_id=chat_id)
        responder = self.create_responder()

        handler = SelectClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video(), "Handler should send video"

    @pytest.mark.asyncio
    async def test_select_clip_no_previous_search(self):
        message = self.create_message('/select 1')
        responder = self.create_responder()

        handler = SelectClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'najpierw' in all_responses.lower() or 'first' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_select_clip_missing_argument(self):
        message = self.create_message('/wybierz')
        responder = self.create_responder()

        handler = SelectClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_select_clip_invalid_index_format(self, mock_db):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))

        message = self.create_message('/wybierz abc', user_id=chat_id)
        responder = self.create_responder()

        handler = SelectClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_select_clip_index_out_of_range(self, mock_db):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))

        message = self.create_message('/select 99', user_id=chat_id)
        responder = self.create_responder()

        handler = SelectClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_select_clip_zero_index(self, mock_db):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))

        message = self.create_message('/wybierz 0', user_id=chat_id)
        responder = self.create_responder()

        handler = SelectClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_select_clip_negative_index(self, mock_db):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))

        message = self.create_message('/wybierz -1', user_id=chat_id)
        responder = self.create_responder()

        handler = SelectClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_select_clip_from_multiple_segments(self, mock_db, mock_ffmpeg):
        chat_id = self.admin_id
        segments = [
            {'id': '1', 'video_path': '/fake/s01e01.mp4', 'start_time': 10.0, 'end_time': 20.0},
            {'id': '2', 'video_path': '/fake/s01e02.mp4', 'start_time': 30.0, 'end_time': 40.0},
            {'id': '3', 'video_path': '/fake/s01e03.mp4', 'start_time': 50.0, 'end_time': 60.0},
        ]
        await mock_db.insert_last_search(chat_id, 'test', json.dumps(segments))
        mock_ffmpeg.add_mock_clip('/fake/s01e02.mp4')

        message = self.create_message('/select 2', user_id=chat_id)
        responder = self.create_responder()

        handler = SelectClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video(), "Handler should send video"

    @pytest.mark.asyncio
    async def test_select_clip_different_aliases(self, mock_db, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {'id': '123', 'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        for command in ('/wybierz', '/select', '/w'):
            await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))
            responder = self.create_responder()
            message = self.create_message(f'{command} 1', user_id=chat_id)

            handler = SelectClipHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_video() or responder.has_sent_text(), f"Handler should respond to {command}"
