import pytest

import bot.responses.not_sending_videos.search_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSearchHandler(BaseTest):

    LONG_QUOTE_WORD_COUNT = 100

    @pytest.mark.asyncio
    async def test_search_existing_quote(self):
        response = self.send_command('/szukaj geniusz')
        self.assert_message_hash_matches(response, expected_key="search_geniusz_results.message")

    @pytest.mark.asyncio
    async def test_search_nonexistent_quote(self):
        response = self.send_command('/szukaj brak_cytatu')
        self.assert_message_hash_matches(response, expected_key="search_brak_cytatu_results.message")

    @pytest.mark.asyncio
    async def test_search_invalid_arguments(self):
        response = self.send_command('/szukaj')
        self.assert_response_contains(response, [msg.get_invalid_args_count_message()])

    @pytest.mark.asyncio
    async def test_search_long_quote_exceeds_limit(self):
        long_quote = " ".join(["słowo"] * self.LONG_QUOTE_WORD_COUNT)
        response = self.send_command(f'/szukaj {long_quote}')
        self.assert_message_hash_matches(response, expected_key="search_long_quote_exceeds_limit.message")

    @pytest.mark.asyncio
    async def test_search_short_alias(self):
        response = self.send_command('/sz geniusz')
        self.assert_message_hash_matches(response, expected_key="search_short_alias_geniusz.message")
