import logging

import pytest

from bot.handlers.administration.create_key_handler import CreateKeyHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestCreateKeyHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_create_key_success(self, mock_db):
        message = self.create_message('/addkey 30 test_key')
        responder = self.create_responder()

        handler = CreateKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'test_key' in all_responses
        assert '30' in all_responses

        key_days = await mock_db.get_subscription_days_by_key('test_key')
        assert key_days == 30, "Key should be created in database"

    @pytest.mark.asyncio
    async def test_create_key_with_spaces_in_name(self, mock_db):
        message = self.create_message('/addkey 15 klucz ze spacjami')
        responder = self.create_responder()

        handler = CreateKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        key_days = await mock_db.get_subscription_days_by_key('klucz ze spacjami')
        assert key_days == 15, "Key with spaces should be created"

    @pytest.mark.asyncio
    async def test_create_key_with_special_characters(self, mock_db):
        message = self.create_message('/addkey 7 klucz!@#$%')
        responder = self.create_responder()

        handler = CreateKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        key_days = await mock_db.get_subscription_days_by_key('klucz!@#$%')
        assert key_days == 7, "Key with special characters should be created"

    @pytest.mark.asyncio
    async def test_create_key_missing_arguments(self, mock_db):
        message = self.create_message('/addkey')
        responder = self.create_responder()

        handler = CreateKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'użyj' in all_responses.lower() or 'usage' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_create_key_missing_key_name(self, mock_db):
        message = self.create_message('/addkey 30')
        responder = self.create_responder()

        handler = CreateKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_create_key_zero_days(self, mock_db):
        message = self.create_message('/addkey 0 zero_key')
        responder = self.create_responder()

        handler = CreateKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        key_days = await mock_db.get_subscription_days_by_key('zero_key')
        assert key_days is None, "Key with 0 days should not be created"

    @pytest.mark.asyncio
    async def test_create_key_negative_days(self, mock_db):
        message = self.create_message('/addkey -10 negative_key')
        responder = self.create_responder()

        handler = CreateKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        key_days = await mock_db.get_subscription_days_by_key('negative_key')
        assert key_days is None, "Key with negative days should not be created"

    @pytest.mark.asyncio
    async def test_create_key_invalid_days_format(self, mock_db):
        message = self.create_message('/addkey abc invalid_key')
        responder = self.create_responder()

        handler = CreateKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        key_days = await mock_db.get_subscription_days_by_key('invalid_key')
        assert key_days is None, "Key with invalid days format should not be created"

    @pytest.mark.asyncio
    async def test_create_key_duplicate(self, mock_db):
        await mock_db.create_subscription_key(30, 'duplicate_key')

        message = self.create_message('/addkey 15 duplicate_key')
        responder = self.create_responder()

        handler = CreateKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'istnieje' in all_responses.lower() or 'exists' in all_responses.lower()

        key_days = await mock_db.get_subscription_days_by_key('duplicate_key')
        assert key_days == 30, "Original key should remain unchanged"

    @pytest.mark.asyncio
    async def test_create_key_large_days_value(self, mock_db):
        message = self.create_message('/addkey 99999 long_key')
        responder = self.create_responder()

        handler = CreateKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        key_days = await mock_db.get_subscription_days_by_key('long_key')
        assert key_days == 99999, "Key with large days value should be created"
