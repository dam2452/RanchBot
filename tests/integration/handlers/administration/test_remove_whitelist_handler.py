import logging

import pytest

from bot.handlers.administration.remove_whitelist_handler import RemoveWhitelistHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestRemoveWhitelistHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_remove_whitelist_success(self, mock_db):
        await self.add_test_user(user_id=44444)

        message = self.create_message('/removewhitelist 44444')
        responder = self.create_responder()

        handler = RemoveWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '44444' in all_responses

        user_exists = await mock_db.is_user_in_db(44444)
        assert not user_exists, "User should be removed from whitelist"

    @pytest.mark.asyncio
    async def test_remove_whitelist_nonexistent_user(self, mock_db):
        message = self.create_message('/rmw 99999')
        responder = self.create_responder()

        handler = RemoveWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'nie' in all_responses.lower() or 'not' in all_responses.lower() or 'brak' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_remove_whitelist_missing_argument(self, mock_db):
        message = self.create_message('/removewhitelist')
        responder = self.create_responder()

        handler = RemoveWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_remove_whitelist_invalid_user_id_format(self, mock_db):
        message = self.create_message('/removewhitelist abc')
        responder = self.create_responder()

        handler = RemoveWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_remove_whitelist_negative_user_id(self, mock_db):
        message = self.create_message('/removewhitelist -123')
        responder = self.create_responder()

        handler = RemoveWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_remove_whitelist_user_with_subscription(self, mock_db):
        await self.add_test_user(user_id=44445, subscription_days=30)

        message = self.create_message('/removewhitelist 44445')
        responder = self.create_responder()

        handler = RemoveWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        user_exists = await mock_db.is_user_in_db(44445)
        assert not user_exists, "User with subscription should be removed"
        subscription_end = await mock_db.get_user_subscription(44445)
        assert subscription_end is None, "Subscription should also be removed"
