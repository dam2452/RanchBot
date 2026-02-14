import logging

import pytest

from bot.handlers.administration.add_whitelist_handler import AddWhitelistHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestAddWhitelistHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_add_whitelist_success(self, mock_db):
        message = self.create_message('/addwhitelist 33333')
        responder = self.create_responder()

        handler = AddWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '33333' in all_responses

        user_exists = await mock_db.is_user_in_db(33333)
        assert user_exists, "User should be added to whitelist"

    @pytest.mark.asyncio
    async def test_add_whitelist_duplicate_user(self):
        await self.add_test_user(user_id=33334)

        message = self.create_message('/addw 33334')
        responder = self.create_responder()

        handler = AddWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"

    @pytest.mark.asyncio
    async def test_add_whitelist_missing_argument(self):
        message = self.create_message('/addwhitelist')
        responder = self.create_responder()

        handler = AddWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_add_whitelist_invalid_user_id_format(self):
        message = self.create_message('/addwhitelist abc')
        responder = self.create_responder()

        handler = AddWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_add_whitelist_negative_user_id(self):
        message = self.create_message('/addwhitelist -123')
        responder = self.create_responder()

        handler = AddWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_add_whitelist_zero_user_id(self, mock_db):
        message = self.create_message('/addwhitelist 0')
        responder = self.create_responder()

        handler = AddWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        user_exists = await mock_db.is_user_in_db(0)
        assert user_exists, "User with ID 0 should be added"

    @pytest.mark.asyncio
    async def test_add_whitelist_large_user_id(self, mock_db):
        large_id = 999999999999
        message = self.create_message(f'/addwhitelist {large_id}')
        responder = self.create_responder()

        handler = AddWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        user_exists = await mock_db.is_user_in_db(large_id)
        assert user_exists, "User with large ID should be added"
