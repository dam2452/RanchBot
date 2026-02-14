import logging

import pytest

from bot.handlers.not_sending_videos.serial_context_handler import SerialContextHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestSerialContextHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_serial_show_current(self):
        user_id = self.admin_id

        message = self.create_message('/serial', user_id=user_id)
        responder = self.create_responder()

        handler = SerialContextHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send current series"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert len(all_responses) > 0

    @pytest.mark.asyncio
    async def test_serial_change_series_valid(self):
        user_id = self.admin_id

        message = self.create_message('/series ranczo', user_id=user_id)
        responder = self.create_responder()

        handler = SerialContextHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should confirm series change"

    @pytest.mark.asyncio
    async def test_serial_change_series_invalid(self):
        user_id = self.admin_id

        message = self.create_message('/ser nonexistent_series', user_id=user_id)
        responder = self.create_responder()

        handler = SerialContextHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'nieznany' in all_responses.lower() or 'unknown' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_serial_too_many_arguments(self):
        user_id = self.admin_id

        message = self.create_message('/serial ranczo extra args', user_id=user_id)
        responder = self.create_responder()

        handler = SerialContextHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_serial_case_insensitive(self):
        user_id = self.admin_id

        message = self.create_message('/serial RANCZO', user_id=user_id)
        responder = self.create_responder()

        handler = SerialContextHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should accept uppercase series name"

    @pytest.mark.asyncio
    async def test_serial_different_aliases(self):
        user_id = self.admin_id

        for command in ('/serial', '/series', '/ser'):
            responder = self.create_responder()
            message = self.create_message(command, user_id=user_id)

            handler = SerialContextHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to {command}"
