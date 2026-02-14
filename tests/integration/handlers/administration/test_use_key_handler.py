import logging

import pytest

from bot.handlers.administration.use_key_handler import SaveUserKeyHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestUseKeyHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_use_key_success(self, mock_db):
        await mock_db.create_subscription_key(30, 'valid_key')
        user_id = 10001

        message = self.create_message('/key valid_key', user_id=user_id, username='testuser')
        responder = self.create_responder()

        handler = SaveUserKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '30' in all_responses

        subscription_end = await mock_db.get_user_subscription(user_id)
        assert subscription_end is not None, "Subscription should be added"

        key_exists = await mock_db.get_subscription_days_by_key('valid_key')
        assert key_exists is None, "Key should be removed after use"

    @pytest.mark.asyncio
    async def test_use_key_creates_user_if_not_exists(self, mock_db):
        await mock_db.create_subscription_key(15, 'new_user_key')
        user_id = 10002

        message = self.create_message('/klucz new_user_key', user_id=user_id, username='newuser', full_name='New User')
        responder = self.create_responder()

        handler = SaveUserKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        user_exists = await mock_db.is_user_in_db(user_id)
        assert user_exists, "User should be created"

    @pytest.mark.asyncio
    async def test_use_key_invalid_key(self):
        message = self.create_message('/key invalid_key', user_id=10003)
        responder = self.create_responder()

        handler = SaveUserKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'niepoprawny' in all_responses.lower() or 'invalid' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_use_key_missing_argument(self):
        message = self.create_message('/key')
        responder = self.create_responder()

        handler = SaveUserKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_use_key_with_spaces(self, mock_db):
        await mock_db.create_subscription_key(7, 'key_with_spaces')
        user_id = 10004

        message = self.create_message('/key key_with_spaces', user_id=user_id)
        responder = self.create_responder()

        handler = SaveUserKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        subscription_end = await mock_db.get_user_subscription(user_id)
        assert subscription_end is not None, "Subscription should be added"

    @pytest.mark.asyncio
    async def test_use_key_already_used(self, mock_db):
        await mock_db.create_subscription_key(30, 'one_time_key')

        message1 = self.create_message('/key one_time_key', user_id=10005)
        responder1 = self.create_responder()
        handler1 = SaveUserKeyHandler(message1, responder1, logger)
        await handler1.handle()

        message2 = self.create_message('/key one_time_key', user_id=10006)
        responder2 = self.create_responder()
        handler2 = SaveUserKeyHandler(message2, responder2, logger)
        await handler2.handle()

        assert responder2.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder2.get_all_text_responses())
        assert 'niepoprawny' in all_responses.lower() or 'invalid' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_use_key_extends_existing_subscription(self, mock_db):
        await mock_db.create_subscription_key(15, 'extend_key')
        user_id = 10007
        await self.add_test_user(user_id=user_id, subscription_days=10)

        message = self.create_message('/key extend_key', user_id=user_id)
        responder = self.create_responder()

        handler = SaveUserKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"

    @pytest.mark.asyncio
    async def test_use_key_different_aliases(self, mock_db):
        for i, command in enumerate(['/klucz', '/key'], start=1):
            await mock_db.create_subscription_key(30, f'test_key_{i}')
            user_id = 10010 + i

            message = self.create_message(f'{command} test_key_{i}', user_id=user_id)
            responder = self.create_responder()

            handler = SaveUserKeyHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to {command}"
