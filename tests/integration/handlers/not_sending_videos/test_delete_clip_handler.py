import logging

import pytest

from bot.handlers.not_sending_videos.delete_clip_handler import DeleteClipHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestDeleteClipHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_delete_clip_by_name_success(self, mock_db):
        user_id = self.admin_id
        await mock_db.save_clip(
            chat_id=user_id,
            user_id=user_id,
            clip_name='test_clip',
            video_data=b'fake_video',
            start_time=0.0,
            end_time=5.0,
            duration=5.0,
        )

        message = self.create_message('/usunklip test_clip', user_id=user_id)
        responder = self.create_responder()

        handler = DeleteClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        clips = await mock_db.get_saved_clips(user_id)
        assert len(clips) == 0, "Clip should be deleted"

    @pytest.mark.asyncio
    async def test_delete_clip_by_index_success(self, mock_db):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data1', 0.0, 5.0, 5.0)
        await mock_db.save_clip(user_id, user_id, 'clip2', b'data2', 0.0, 10.0, 10.0)
        await mock_db.save_clip(user_id, user_id, 'clip3', b'data3', 0.0, 15.0, 15.0)

        message = self.create_message('/uk 2', user_id=user_id)
        responder = self.create_responder()

        handler = DeleteClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        clips = await mock_db.get_saved_clips(user_id)
        assert len(clips) == 2, "One clip should be deleted"
        assert clips[0].name == 'clip1'
        assert clips[1].name == 'clip3'

    @pytest.mark.asyncio
    async def test_delete_clip_nonexistent_name(self, mock_db):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'existing_clip', b'data', 0.0, 5.0, 5.0)

        message = self.create_message('/deleteclip nonexistent', user_id=user_id)
        responder = self.create_responder()

        handler = DeleteClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        clips = await mock_db.get_saved_clips(user_id)
        assert len(clips) == 1, "Existing clip should remain"

    @pytest.mark.asyncio
    async def test_delete_clip_invalid_index(self, mock_db):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data', 0.0, 5.0, 5.0)

        message = self.create_message('/usunklip 5', user_id=user_id)
        responder = self.create_responder()

        handler = DeleteClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        clips = await mock_db.get_saved_clips(user_id)
        assert len(clips) == 1, "Clip should not be deleted"

    @pytest.mark.asyncio
    async def test_delete_clip_no_saved_clips(self):
        user_id = self.admin_id

        message = self.create_message('/usunklip test', user_id=user_id)
        responder = self.create_responder()

        handler = DeleteClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'nie masz' in all_responses.lower() or 'no clips' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_delete_clip_missing_argument(self):
        message = self.create_message('/usunklip')
        responder = self.create_responder()

        handler = DeleteClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_delete_clip_zero_index(self, mock_db):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data', 0.0, 5.0, 5.0)

        message = self.create_message('/usunklip 0', user_id=user_id)
        responder = self.create_responder()

        handler = DeleteClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_delete_clip_negative_index(self, mock_db):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data', 0.0, 5.0, 5.0)

        message = self.create_message('/usunklip -1', user_id=user_id)
        responder = self.create_responder()

        handler = DeleteClipHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_delete_clip_first_of_many(self, mock_db):
        user_id = self.admin_id
        for i in range(5):
            await mock_db.save_clip(user_id, user_id, f'clip{i}', b'data', 0.0, 5.0, 5.0)

        message = self.create_message('/usunklip 1', user_id=user_id)
        responder = self.create_responder()

        handler = DeleteClipHandler(message, responder, logger)
        await handler.handle()

        clips = await mock_db.get_saved_clips(user_id)
        assert len(clips) == 4
        assert clips[0].name == 'clip1'
