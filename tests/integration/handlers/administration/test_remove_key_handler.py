import logging

import pytest

from bot.handlers.administration.remove_key_handler import RemoveKeyHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestRemoveKeyHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_remove_key_success(self, mock_db):
        await mock_db.create_subscription_key(30, 'key_to_remove')

        message = self.create_message('/removekey key_to_remove')
        responder = self.create_responder()

        handler = RemoveKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'usuń' in all_responses.lower() or 'removed' in all_responses.lower() or 'key_to_remove' in all_responses

        key_days = await mock_db.get_subscription_days_by_key('key_to_remove')
        assert key_days is None, "Key should be removed from database"

    @pytest.mark.asyncio
    async def test_remove_key_with_spaces(self, mock_db):
        await mock_db.create_subscription_key(15, 'klucz_ze_spacjami')

        message = self.create_message('/rmk klucz_ze_spacjami')
        responder = self.create_responder()

        handler = RemoveKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        key_days = await mock_db.get_subscription_days_by_key('klucz_ze_spacjami')
        assert key_days is None, "Key with spaces should be removed"

    @pytest.mark.asyncio
    async def test_remove_key_nonexistent(self):
        message = self.create_message('/removekey nonexistent_key')
        responder = self.create_responder()

        handler = RemoveKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'nie' in all_responses.lower() or 'not' in all_responses.lower() or 'failure' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_remove_key_missing_argument(self):
        message = self.create_message('/removekey')
        responder = self.create_responder()

        handler = RemoveKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'podaj' in all_responses.lower() or 'example' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_remove_key_with_special_characters(self, mock_db):
        await mock_db.create_subscription_key(10, 'key!@#$%')

        message = self.create_message('/removekey key!@#$%')
        responder = self.create_responder()

        handler = RemoveKeyHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        key_days = await mock_db.get_subscription_days_by_key('key!@#$%')
        assert key_days is None, "Key with special characters should be removed"
