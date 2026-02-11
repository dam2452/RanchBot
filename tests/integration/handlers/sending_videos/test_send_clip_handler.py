import logging

import pytest

from bot.handlers.sending_videos.send_clip_handler import SendClipHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestSendClipHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_send_clip_by_name_success(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'test_clip', b'fake_video', 0.0, 5.0, 5.0)
        mock_ffmpeg.add_mock_clip_from_bytes(b'fake_video')

        message = self.create_message('/wyslij test_clip', user_id=user_id)
        responder = self.create_responder()

        handler = SendClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video(), "Handler should send video"

    @pytest.mark.asyncio
    async def test_send_clip_by_index_success(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data1', 0.0, 5.0, 5.0)
        await mock_db.save_clip(user_id, user_id, 'clip2', b'data2', 0.0, 10.0, 10.0)
        mock_ffmpeg.add_mock_clip_from_bytes(b'data2')

        message = self.create_message('/send 2', user_id=user_id)
        responder = self.create_responder()

        handler = SendClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_video(), "Handler should send video"

    @pytest.mark.asyncio
    async def test_send_clip_nonexistent_name(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data', 0.0, 5.0, 5.0)

        message = self.create_message('/w nonexistent', user_id=user_id)
        responder = self.create_responder()

        handler = SendClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        assert not responder.has_sent_video(), "Handler should not send video"

    @pytest.mark.asyncio
    async def test_send_clip_invalid_index(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data', 0.0, 5.0, 5.0)

        message = self.create_message('/wyslij 5', user_id=user_id)
        responder = self.create_responder()

        handler = SendClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        assert not responder.has_sent_video()

    @pytest.mark.asyncio
    async def test_send_clip_no_saved_clips(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id

        message = self.create_message('/wyslij test', user_id=user_id)
        responder = self.create_responder()

        handler = SendClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        assert not responder.has_sent_video()

    @pytest.mark.asyncio
    async def test_send_clip_missing_argument(self, mock_db, mock_ffmpeg):
        message = self.create_message('/wyslij')
        responder = self.create_responder()

        handler = SendClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_send_clip_different_aliases(self, mock_db, mock_ffmpeg):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'test', b'data', 0.0, 5.0, 5.0)
        mock_ffmpeg.add_mock_clip_from_bytes(b'data')

        for command in ['/wyslij', '/send', '/w']:
            responder = self.create_responder()
            message = self.create_message(f'{command} test', user_id=user_id)

            handler = SendClipHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_video() or responder.has_sent_text(), f"Handler should respond to {command}"
