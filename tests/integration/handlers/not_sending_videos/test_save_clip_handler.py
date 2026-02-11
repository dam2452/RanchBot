import json
import logging

import pytest

from bot.database.models import ClipType
from bot.handlers.not_sending_videos.save_clip_handler import SaveClipHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestSaveClipHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_save_clip_success(self, mock_db, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {
            'video_path': '/fake/path.mp4',
            'episode_info': {'season': 1, 'episode_number': 1},
        }
        mock_db._last_clips[chat_id] = {
            'segment': json.dumps(segment),
            'clip_type': ClipType.MANUAL,
            'adjusted_start_time': 0.0,
            'adjusted_end_time': 5.0,
        }
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        message = self.create_message('/zapisz test_clip', user_id=chat_id)
        responder = self.create_responder()

        handler = SaveClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        clips = await mock_db.get_saved_clips(chat_id)
        assert len(clips) == 1
        assert clips[0].name == 'test_clip'

    @pytest.mark.asyncio
    async def test_save_clip_no_last_clip(self):
        message = self.create_message('/save my_clip')
        responder = self.create_responder()

        handler = SaveClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'nie' in all_responses.lower() or 'no' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_save_clip_missing_name(self):
        message = self.create_message('/zapisz')
        responder = self.create_responder()

        handler = SaveClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_save_clip_numeric_name(self, mock_db):
        chat_id = self.admin_id
        mock_db._last_clips[chat_id] = {
            'segment': json.dumps({'video_path': '/fake/path.mp4', 'episode_info': {}}),
            'clip_type': ClipType.MANUAL,
            'adjusted_start_time': 0.0,
            'adjusted_end_time': 5.0,
        }

        message = self.create_message('/zapisz 123', user_id=chat_id)
        responder = self.create_responder()

        handler = SaveClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'cyfr' in all_responses.lower() or 'numeric' in all_responses.lower() or 'liczb' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_save_clip_duplicate_name(self, mock_db, mock_ffmpeg):
        chat_id = self.admin_id
        await mock_db.save_clip(chat_id, chat_id, 'existing_clip', b'data', 0.0, 5.0, 5.0)

        mock_db._last_clips[chat_id] = {
            'segment': json.dumps({'video_path': '/fake/path.mp4', 'episode_info': {}}),
            'clip_type': ClipType.MANUAL,
            'adjusted_start_time': 0.0,
            'adjusted_end_time': 5.0,
        }
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        message = self.create_message('/zapisz existing_clip', user_id=chat_id)
        responder = self.create_responder()

        handler = SaveClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'istnieje' in all_responses.lower() or 'exists' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_save_clip_name_too_long(self, mock_db):
        chat_id = self.admin_id
        mock_db._last_clips[chat_id] = {
            'segment': json.dumps({'video_path': '/fake/path.mp4', 'episode_info': {}}),
            'clip_type': ClipType.MANUAL,
            'adjusted_start_time': 0.0,
            'adjusted_end_time': 5.0,
        }

        very_long_name = 'a' * 200
        message = self.create_message(f'/zapisz {very_long_name}', user_id=chat_id)
        responder = self.create_responder()

        handler = SaveClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_save_clip_with_special_characters(self, mock_db, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {
            'video_path': '/fake/path.mp4',
            'episode_info': {'season': 1, 'episode_number': 1},
        }
        mock_db._last_clips[chat_id] = {
            'segment': json.dumps(segment),
            'clip_type': ClipType.MANUAL,
            'adjusted_start_time': 0.0,
            'adjusted_end_time': 5.0,
        }
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        message = self.create_message('/zapisz clip_name_!@#', user_id=chat_id)
        responder = self.create_responder()

        handler = SaveClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should process special characters"

    @pytest.mark.asyncio
    async def test_save_clip_different_aliases(self, mock_db, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {
            'video_path': '/fake/path.mp4',
            'episode_info': {'season': 1, 'episode_number': 1},
        }
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        for i, command in enumerate(['/zapisz', '/save', '/z']):
            mock_db._last_clips[chat_id] = {
                'segment': json.dumps(segment),
                'clip_type': ClipType.MANUAL,
                'adjusted_start_time': 0.0,
                'adjusted_end_time': 5.0,
            }

            responder = self.create_responder()
            message = self.create_message(f'{command} clip{i}', user_id=chat_id)

            handler = SaveClipHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to {command}"
