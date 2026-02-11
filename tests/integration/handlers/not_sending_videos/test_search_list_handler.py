import json
import logging

import pytest

from bot.handlers.not_sending_videos.search_list_handler import SearchListHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestSearchListHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_search_list_with_previous_search(self, mock_db, mock_es):
        chat_id = self.admin_id
        segments = [
            {'text': 'test segment 1', 'start': 0.0, 'end': 5.0},
            {'text': 'test segment 2', 'start': 5.0, 'end': 10.0},
        ]
        await mock_db.insert_last_search(chat_id, 'test query', json.dumps(segments))

        message = self.create_message('/lista', user_id=chat_id)
        responder = self.create_responder()

        handler = SearchListHandler(message, responder, logger)
        await handler.handle()

        assert len(responder.documents) > 0, "Handler should send document"

    @pytest.mark.asyncio
    async def test_search_list_no_previous_search(self, mock_db, mock_es):
        chat_id = self.admin_id

        message = self.create_message('/list', user_id=chat_id)
        responder = self.create_responder()

        handler = SearchListHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        all_responses = ' '.join(responder.get_all_text_responses())
        assert 'brak' in all_responses.lower() or 'no' in all_responses.lower()

    @pytest.mark.asyncio
    async def test_search_list_empty_segments(self, mock_db, mock_es):
        chat_id = self.admin_id
        await mock_db.insert_last_search(chat_id, 'test', json.dumps([]))

        message = self.create_message('/l', user_id=chat_id)
        responder = self.create_responder()

        handler = SearchListHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"

    @pytest.mark.asyncio
    async def test_search_list_with_special_characters_in_query(self, mock_db, mock_es):
        chat_id = self.admin_id
        segments = [{'text': 'test', 'start': 0.0, 'end': 5.0}]
        await mock_db.insert_last_search(chat_id, 'query!@#$%', json.dumps(segments))

        message = self.create_message('/lista', user_id=chat_id)
        responder = self.create_responder()

        handler = SearchListHandler(message, responder, logger)
        await handler.handle()

        assert len(responder.documents) > 0, "Handler should handle special characters"

    @pytest.mark.asyncio
    async def test_search_list_different_aliases(self, mock_db, mock_es):
        chat_id = self.admin_id
        segments = [{'text': 'test', 'start': 0.0, 'end': 5.0}]
        await mock_db.insert_last_search(chat_id, 'test', json.dumps(segments))

        for command in ['/lista', '/list', '/l']:
            responder = self.create_responder()
            message = self.create_message(command, user_id=chat_id)

            handler = SearchListHandler(message, responder, logger)
            await handler.handle()

            assert len(responder.documents) > 0 or responder.has_sent_text(), f"Handler should respond to {command}"
