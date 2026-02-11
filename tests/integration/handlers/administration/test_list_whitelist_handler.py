import logging

import pytest

from bot.handlers.administration.list_whitelist_handler import ListWhitelistHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestListWhitelistHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_list_whitelist_with_multiple_users(self):
        await self.add_test_user(user_id=55551, username='user1')
        await self.add_test_user(user_id=55552, username='user2')
        await self.add_test_user(user_id=55553, username='user3')

        message = self.create_message('/listwhitelist')
        responder = self.create_responder()

        handler = ListWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send whitelist"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '55551' in all_responses or 'user1' in all_responses
        assert '55552' in all_responses or 'user2' in all_responses
        assert '55553' in all_responses or 'user3' in all_responses

    @pytest.mark.asyncio
    async def test_list_whitelist_when_empty(self):
        message = self.create_message('/lw')
        responder = self.create_responder()

        handler = ListWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send empty message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'brak' in all_responses.lower() or 'empty' in all_responses.lower() or 'pusta' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_list_whitelist_with_single_user(self):
        await self.add_test_user(user_id=55554, username='single_user')

        message = self.create_message('/listwhitelist')
        responder = self.create_responder()

        handler = ListWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send whitelist"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '55554' in all_responses or 'single_user' in all_responses

    @pytest.mark.asyncio
    async def test_list_whitelist_shows_user_details(self):
        await self.add_test_user(
            user_id=55555,
            username='detailed_user',
            full_name='Full Name Test',
        )

        message = self.create_message('/listwhitelist')
        responder = self.create_responder()

        handler = ListWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send whitelist"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '55555' in all_responses

    @pytest.mark.asyncio
    async def test_list_whitelist_includes_admin_users(self):
        message = self.create_message('/listwhitelist')
        responder = self.create_responder()

        handler = ListWhitelistHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send whitelist"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert str(self.admin_id) in all_responses
