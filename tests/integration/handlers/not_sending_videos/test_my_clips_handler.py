import logging

import pytest

from bot.handlers.not_sending_videos.my_clips_handler import MyClipsHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestMyClipsHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_my_clips_with_saved_clips(self, mock_db, mock_es):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'clip1', b'data1', 0.0, 5.0, 5.0)
        await mock_db.save_clip(user_id, user_id, 'clip2', b'data2', 5.0, 10.0, 5.0)

        message = self.create_message('/mojeklipy', user_id=user_id)
        responder = self.create_responder()

        handler = MyClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send clips list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'clip1' in all_responses
        assert 'clip2' in all_responses

    @pytest.mark.asyncio
    async def test_my_clips_with_no_clips(self, mock_db, mock_es):
        user_id = self.admin_id

        message = self.create_message('/myclips', user_id=user_id)
        responder = self.create_responder()

        handler = MyClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'brak' in all_responses.lower() or 'no' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_my_clips_with_single_clip(self, mock_db, mock_es):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'only_clip', b'data', 0.0, 5.0, 5.0)

        message = self.create_message('/mk', user_id=user_id)
        responder = self.create_responder()

        handler = MyClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send clip"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'only_clip' in all_responses

    @pytest.mark.asyncio
    async def test_my_clips_with_many_clips(self, mock_db, mock_es):
        user_id = self.admin_id
        for i in range(10):
            await mock_db.save_clip(user_id, user_id, f'clip{i}', b'data', 0.0, 5.0, 5.0)

        message = self.create_message('/mojeklipy', user_id=user_id)
        responder = self.create_responder()

        handler = MyClipsHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send clips list"
        all_responses = ' '.join(responder.get_all_text_responses())
        for i in range(10):
            assert f'clip{i}' in all_responses

    @pytest.mark.asyncio
    async def test_my_clips_different_aliases(self, mock_db, mock_es):
        user_id = self.admin_id
        await mock_db.save_clip(user_id, user_id, 'test_clip', b'data', 0.0, 5.0, 5.0)

        for command in ['/mojeklipy', '/myclips', '/mk']:
            responder = self.create_responder()
            message = self.create_message(command, user_id=user_id)

            handler = MyClipsHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to {command}"
