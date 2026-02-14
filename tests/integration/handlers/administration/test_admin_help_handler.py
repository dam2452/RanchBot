import logging

import pytest

from bot.handlers.administration.admin_help_handler import AdminHelpHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestAdminHelpHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_admin_help_basic_message(self):
        message = self.create_message('/admin')
        responder = self.create_responder()

        handler = AdminHelpHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send help message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert len(all_responses) > 50, "Help message should contain substantial content"

    @pytest.mark.asyncio
    async def test_admin_help_shortcuts_with_skroty(self):
        message = self.create_message('/admin skróty')
        responder = self.create_responder()

        handler = AdminHelpHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send shortcuts message"

    @pytest.mark.asyncio
    async def test_admin_help_shortcuts_with_skroty_without_diacritics(self):
        message = self.create_message('/admin skroty')
        responder = self.create_responder()

        handler = AdminHelpHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send shortcuts message"

    @pytest.mark.asyncio
    async def test_admin_help_shortcuts_with_skrot(self):
        message = self.create_message('/admin skrót')
        responder = self.create_responder()

        handler = AdminHelpHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send shortcuts message"

    @pytest.mark.asyncio
    async def test_admin_help_with_random_argument(self):
        message = self.create_message('/admin random_text')
        responder = self.create_responder()

        handler = AdminHelpHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send basic help message"

    @pytest.mark.asyncio
    async def test_admin_help_with_mixed_case_shortcuts(self):
        message = self.create_message('/admin SKRÓTY')
        responder = self.create_responder()

        handler = AdminHelpHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send shortcuts message (case insensitive)"

    @pytest.mark.asyncio
    async def test_admin_help_shortcuts_in_sentence(self):
        message = self.create_message('/admin pokaż mi skróty proszę')
        responder = self.create_responder()

        handler = AdminHelpHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send shortcuts message when keyword is in sentence"
