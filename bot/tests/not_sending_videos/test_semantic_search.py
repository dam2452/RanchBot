import pytest

import bot.responses.not_sending_videos.semantic_search_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSemanticSearchHandler(BaseTest):

    LONG_QUERY_WORD_COUNT = 100

    @pytest.mark.asyncio
    async def test_semantic_search_existing_concept(self):
        response = self.send_command('/sens ucieczka od rodziny')
        self.assert_message_hash_matches(response, expected_key="semantic_search_ucieczka.message")

    @pytest.mark.asyncio
    async def test_semantic_search_invalid_arguments(self):
        response = self.send_command('/sens')
        self.assert_response_contains(response, [msg.get_no_query_provided_message()])

    @pytest.mark.asyncio
    async def test_semantic_search_long_query_exceeds_limit(self):
        long_query = " ".join(["słowo"] * self.LONG_QUERY_WORD_COUNT)
        response = self.send_command(f'/sens {long_query}')
        self.assert_message_hash_matches(
            response, expected_key="semantic_search_long_query_exceeds_limit.message",
        )

    @pytest.mark.asyncio
    async def test_semantic_search_alias_meaning(self):
        response = self.send_command('/meaning ucieczka od rodziny')
        self.assert_message_hash_matches(response, expected_key="semantic_search_ucieczka.message")

    @pytest.mark.asyncio
    async def test_semantic_search_alias_sen(self):
        response = self.send_command('/sen ucieczka od rodziny')
        self.assert_message_hash_matches(response, expected_key="semantic_search_ucieczka.message")
