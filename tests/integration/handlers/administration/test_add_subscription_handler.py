from datetime import (
    date,
    timedelta,
)
import logging

import pytest

from bot.handlers.administration.add_subscription_handler import AddSubscriptionHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestAddSubscriptionHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_add_subscription_success(self, mock_db):
        await self.add_test_user(user_id=12345, username='test_user')

        message = self.create_message('/addsubscription 12345 30')
        responder = self.create_responder()

        handler = AddSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert '12345' in all_responses

        subscription_end = await mock_db.get_user_subscription(12345)
        assert subscription_end is not None, "Subscription should be added"
        expected_date = date.today() + timedelta(days=30)
        assert subscription_end == expected_date, "Subscription end date should match"

    @pytest.mark.asyncio
    async def test_add_subscription_extend_existing(self):
        await self.add_test_user(user_id=12346, subscription_days=10)

        message = self.create_message('/addsub 12346 20')
        responder = self.create_responder()

        handler = AddSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"

    @pytest.mark.asyncio
    async def test_add_subscription_nonexistent_user(self):
        message = self.create_message('/addsubscription 99999 30')
        responder = self.create_responder()

        handler = AddSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'błąd' in all_responses.lower() or 'error' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_add_subscription_missing_arguments(self):
        message = self.create_message('/addsubscription')
        responder = self.create_responder()

        handler = AddSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_add_subscription_missing_days(self):
        message = self.create_message('/addsubscription 12345')
        responder = self.create_responder()

        handler = AddSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_add_subscription_invalid_user_id_format(self):
        message = self.create_message('/addsubscription abc 30')
        responder = self.create_responder()

        handler = AddSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_add_subscription_invalid_days_format(self):
        await self.add_test_user(user_id=12347)

        message = self.create_message('/addsubscription 12347 abc')
        responder = self.create_responder()

        handler = AddSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_add_subscription_negative_days(self):
        await self.add_test_user(user_id=12348)

        message = self.create_message('/addsubscription 12348 -10')
        responder = self.create_responder()

        handler = AddSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_add_subscription_zero_days(self):
        await self.add_test_user(user_id=12349)

        message = self.create_message('/addsubscription 12349 0')
        responder = self.create_responder()

        handler = AddSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_add_subscription_large_days_value(self, mock_db):
        await self.add_test_user(user_id=12350)

        message = self.create_message('/addsubscription 12350 9999')
        responder = self.create_responder()

        handler = AddSubscriptionHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        subscription_end = await mock_db.get_user_subscription(12350)
        assert subscription_end is not None
