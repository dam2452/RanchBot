import json
import logging

import pytest

from bot.handlers.sending_videos.compile_clips_handler import CompileClipsHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestCompileClipsHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_compile_clips_single_index(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        message = self.create_message('/kompiluj 1', user_id=chat_id)
        responder = self.create_responder()

        handler = CompileClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video() or responder.has_sent_text()

    @pytest.mark.asyncio
    async def test_compile_clips_multiple_indices(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segments = [
            {'video_path': '/fake/s01e01.mp4', 'start_time': 10.0, 'end_time': 20.0},
            {'video_path': '/fake/s01e02.mp4', 'start_time': 30.0, 'end_time': 40.0},
            {'video_path': '/fake/s01e03.mp4', 'start_time': 50.0, 'end_time': 60.0},
        ]
        await mock_db.insert_last_search(chat_id, 'test', json.dumps(segments))
        for seg in segments:
            mock_ffmpeg.add_mock_clip(seg['video_path'])

        message = self.create_message('/compile 1 2 3', user_id=chat_id)
        responder = self.create_responder()

        handler = CompileClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video() or responder.has_sent_text()

    @pytest.mark.asyncio
    async def test_compile_clips_range(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segments = [
            {'video_path': f'/fake/s01e0{i}.mp4', 'start_time': i*10.0, 'end_time': i*10.0+5.0}
            for i in range(1, 6)
        ]
        await mock_db.insert_last_search(chat_id, 'test', json.dumps(segments))
        for seg in segments:
            mock_ffmpeg.add_mock_clip(seg['video_path'])

        message = self.create_message('/kompiluj 1-3', user_id=chat_id)
        responder = self.create_responder()

        handler = CompileClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video() or responder.has_sent_text()

    @pytest.mark.asyncio
    async def test_compile_clips_all_keyword(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segments = [
            {'video_path': f'/fake/s01e0{i}.mp4', 'start_time': i*10.0, 'end_time': i*10.0+5.0}
            for i in range(1, 4)
        ]
        await mock_db.insert_last_search(chat_id, 'test', json.dumps(segments))
        for seg in segments:
            mock_ffmpeg.add_mock_clip(seg['video_path'])

        for keyword in ['all', 'wszystko']:
            responder = self.create_responder()
            message = self.create_message(f'/kompiluj {keyword}', user_id=chat_id)

            handler = CompileClipsHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_video() or responder.has_sent_text()

    @pytest.mark.asyncio
    async def test_compile_clips_no_previous_search(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/kompiluj 1')
        responder = self.create_responder()

        handler = CompileClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_compile_clips_missing_argument(self, mock_db, mock_es, mock_ffmpeg):
        message = self.create_message('/kompiluj')
        responder = self.create_responder()

        handler = CompileClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_compile_clips_invalid_index(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))

        message = self.create_message('/kompiluj abc', user_id=chat_id)
        responder = self.create_responder()

        handler = CompileClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_compile_clips_invalid_range(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segments = [{'video_path': f'/fake/s{i}.mp4', 'start_time': 10.0, 'end_time': 20.0} for i in range(3)]
        await mock_db.insert_last_search(chat_id, 'test', json.dumps(segments))

        message = self.create_message('/kompiluj 5-3', user_id=chat_id)
        responder = self.create_responder()

        handler = CompileClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_compile_clips_out_of_range_index(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))

        message = self.create_message('/kompiluj 99', user_id=chat_id)
        responder = self.create_responder()

        handler = CompileClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_compile_clips_different_aliases(self, mock_db, mock_es, mock_ffmpeg):
        chat_id = self.admin_id
        segment = {'video_path': '/fake/path.mp4', 'start_time': 10.0, 'end_time': 20.0}
        mock_ffmpeg.add_mock_clip('/fake/path.mp4')

        for command in ['/kompiluj', '/compile', '/kom']:
            await mock_db.insert_last_search(chat_id, 'test', json.dumps([segment]))
            responder = self.create_responder()
            message = self.create_message(f'{command} 1', user_id=chat_id)

            handler = CompileClipsHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_video() or responder.has_sent_text(), f"Handler should respond to {command}"
