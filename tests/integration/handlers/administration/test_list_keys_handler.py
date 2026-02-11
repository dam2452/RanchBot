import logging

import pytest

from bot.handlers.administration.list_keys_handler import ListKeysHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class TestListKeysHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_list_keys_when_keys_exist(self, mock_db):
        await mock_db.create_subscription_key(30, 'key1')
        await mock_db.create_subscription_key(15, 'key2')
        await mock_db.create_subscription_key(60, 'key3')

        message = self.create_message('/listkey')
        responder = self.create_responder()

        handler = ListKeysHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send keys list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'key1' in all_responses
        assert 'key2' in all_responses
        assert 'key3' in all_responses
        assert '30' in all_responses
        assert '15' in all_responses
        assert '60' in all_responses

    @pytest.mark.asyncio
    async def test_list_keys_when_no_keys_exist(self):
        message = self.create_message('/listkey')
        responder = self.create_responder()

        handler = ListKeysHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send empty message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'brak' in all_responses.lower() or 'empty' in all_responses.lower() or 'nie ma' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_list_keys_with_single_key(self, mock_db):
        await mock_db.create_subscription_key(7, 'single_key')

        message = self.create_message('/lk')
        responder = self.create_responder()

        handler = ListKeysHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send key"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'single_key' in all_responses
        assert '7' in all_responses

    @pytest.mark.asyncio
    async def test_list_keys_with_special_characters(self, mock_db):
        await mock_db.create_subscription_key(10, 'key!@#')
        await mock_db.create_subscription_key(20, 'klucz ze spacjami')

        message = self.create_message('/listkey')
        responder = self.create_responder()

        handler = ListKeysHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send keys list"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'key!@#' in all_responses
        assert 'klucz ze spacjami' in all_responses
