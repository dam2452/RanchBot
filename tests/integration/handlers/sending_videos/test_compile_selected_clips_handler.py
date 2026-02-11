import logging

import pytest

from bot.handlers.sending_videos.compile_selected_clips_handler import CompileSelectedClipsHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestCompileSelectedClipsHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_compile_selected_clips_success(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data1', 0.0, 5.0, 5.0)
        await mock_db.save_clip(user_id, user_id, 'clip2', b'data2', 0.0, 10.0, 10.0)
        mock_ffmpeg.add_mock_clip_from_bytes(b'data1')
        mock_ffmpeg.add_mock_clip_from_bytes(b'data2')

        message = self.create_message('/połączklipy 1 2', user_id=user_id)
        responder = self.create_responder()

        handler = CompileSelectedClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video() or responder.has_sent_text()

    @pytest.mark.asyncio
    async def test_compile_selected_clips_single_clip(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data1', 0.0, 5.0, 5.0)
        mock_ffmpeg.add_mock_clip_from_bytes(b'data1')

        message = self.create_message('/polaczklipy 1', user_id=user_id)
        responder = self.create_responder()

        handler = CompileSelectedClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should require at least 2 clips"

    @pytest.mark.asyncio
    async def test_compile_selected_clips_no_saved_clips(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id

        message = self.create_message('/concatclips 1 2', user_id=user_id)
        responder = self.create_responder()

        handler = CompileSelectedClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'brak' in all_responses.lower() or 'no' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_compile_selected_clips_missing_argument(self, mock_db, mock_ffmpeg):
        message = self.create_message('/połączklipy')
        responder = self.create_responder()

        handler = CompileSelectedClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_compile_selected_clips_invalid_index(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data1', 0.0, 5.0, 5.0)

        message = self.create_message('/połączklipy 1 99', user_id=user_id)
        responder = self.create_responder()

        handler = CompileSelectedClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_compile_selected_clips_invalid_format(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data1', 0.0, 5.0, 5.0)

        message = self.create_message('/połączklipy abc def', user_id=user_id)
        responder = self.create_responder()

        handler = CompileSelectedClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_compile_selected_clips_zero_index(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data1', 0.0, 5.0, 5.0)
        await mock_db.save_clip(user_id, user_id, 'clip2', b'data2', 0.0, 10.0, 10.0)

        message = self.create_message('/połączklipy 0 1', user_id=user_id)
        responder = self.create_responder()

        handler = CompileSelectedClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_compile_selected_clips_many_clips(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        for i in range(5):
            await mock_db.save_clip(user_id, user_id, f'clip{i}', b'data', 0.0, 5.0, 5.0)
            mock_ffmpeg.add_mock_clip_from_bytes(b'data')

        message = self.create_message('/połączklipy 1 2 3 4 5', user_id=user_id)
        responder = self.create_responder()

        handler = CompileSelectedClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video() or responder.has_sent_text()

    @pytest.mark.asyncio
    async def test_compile_selected_clips_different_aliases(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data1', 0.0, 5.0, 5.0)
        await mock_db.save_clip(user_id, user_id, 'clip2', b'data2', 0.0, 10.0, 10.0)
        mock_ffmpeg.add_mock_clip_from_bytes(b'data1')
        mock_ffmpeg.add_mock_clip_from_bytes(b'data2')

        for command in ['/połączklipy', '/polaczklipy', '/concatclips', '/pk']:
            responder = self.create_responder()
            message = self.create_message(f'{command} 1 2', user_id=user_id)

            handler = CompileSelectedClipsHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_video() or responder.has_sent_text(), f"Handler should respond to {command}"
