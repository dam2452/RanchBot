import logging

import pytest

from bot.handlers.administration.subscription_status_handler import SubscriptionStatusHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestSubscriptionStatusHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_subscription_status_with_active_subscription(self):
        user_id = self.admin_id
        await self.make_user_subscriber(user_id, days=30)

        message = self.create_message('/subscription', user_id=user_id)
        responder = self.create_responder()

        handler = SubscriptionStatusHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send status message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'subskrypcji' in all_responses.lower() or 'subscription' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_subscription_status_without_subscription(self):
        user_id = 22222
        await self.add_test_user(user_id=user_id)

        message = self.create_message('/sub', user_id=user_id)
        responder = self.create_responder()

        handler = SubscriptionStatusHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'najpierw' in all_responses.lower() or 'first' in all_responses.lower() or 'nie' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_subscription_status_with_expired_subscription(self):
        user_id = 22223
        await self.add_test_user(user_id=user_id, subscription_days=-5)

        message = self.create_message('/subskrypcja', user_id=user_id)
        responder = self.create_responder()

        handler = SubscriptionStatusHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send status message"

    @pytest.mark.asyncio
    async def test_subscription_status_shows_correct_days_remaining(self):
        user_id = 22224
        await self.add_test_user(user_id=user_id, subscription_days=15)

        message = self.create_message('/subscription', user_id=user_id)
        responder = self.create_responder()

        handler = SubscriptionStatusHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send status message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '15' in all_responses or '14' in all_responses

    @pytest.mark.asyncio
    async def test_subscription_status_with_different_aliases(self):
        user_id = self.admin_id
        await self.make_user_subscriber(user_id, days=7)

        for command in ('/subskrypcja', '/subscription', '/sub'):
            responder = self.create_responder()
            message = self.create_message(command, user_id=user_id)

            handler = SubscriptionStatusHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to {command}"
