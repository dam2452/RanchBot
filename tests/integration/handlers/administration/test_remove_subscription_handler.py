import logging

import pytest

from bot.handlers.administration.remove_subscription_handler import RemoveSubscriptionHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestRemoveSubscriptionHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_remove_subscription_success(self, mock_db):
        await self.add_test_user(user_id=11111, subscription_days=30)

        message = self.create_message('/removesubscription 11111')
        responder = self.create_responder()

        handler = RemoveSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '11111' in all_responses

        subscription_end = await mock_db.get_user_subscription(11111)
        assert subscription_end is None, "Subscription should be removed"

    @pytest.mark.asyncio
    async def test_remove_subscription_user_without_subscription(self):
        await self.add_test_user(user_id=11112)

        message = self.create_message('/rmsub 11112')
        responder = self.create_responder()

        handler = RemoveSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"

    @pytest.mark.asyncio
    async def test_remove_subscription_missing_argument(self):
        message = self.create_message('/removesubscription')
        responder = self.create_responder()

        handler = RemoveSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_remove_subscription_invalid_user_id_format(self):
        message = self.create_message('/removesubscription abc')
        responder = self.create_responder()

        handler = RemoveSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_remove_subscription_negative_user_id(self):
        message = self.create_message('/removesubscription -123')
        responder = self.create_responder()

        handler = RemoveSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_remove_subscription_nonexistent_user(self):
        message = self.create_message('/removesubscription 99999')
        responder = self.create_responder()

        handler = RemoveSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
