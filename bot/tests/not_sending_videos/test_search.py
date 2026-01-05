import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSearchHandler(BaseTest):

    LONG_QUOTE_WORD_COUNT = 100

    @pytest.mark.asyncio
    async def test_search_existing_quote(self):
        response = await self.send_command('/szukaj geniusz')
        self.assert_message_hash_matches(response, expected_key="search_geniusz_results.message")

    @pytest.mark.asyncio
    async def test_search_nonexistent_quote(self):
        response = await self.send_command('/szukaj brak_cytatu')
        self.assert_message_hash_matches(response, expected_key="search_brak_cytatu_results.message")

    @pytest.mark.asyncio
    async def test_search_invalid_arguments(self):
        response = await self.send_command('/szukaj')
        await self.assert_response_contains(response, [await self.get_response(RK.INVALID_ARGS_COUNT)])

    @pytest.mark.asyncio
    async def test_search_long_quote_exceeds_limit(self):
        long_quote = " ".join(["słowo"] * self.LONG_QUOTE_WORD_COUNT)
        response = await self.send_command(f'/szukaj {long_quote}')
        self.assert_message_hash_matches(response, expected_key="search_long_quote_exceeds_limit.message")

    @pytest.mark.asyncio
    async def test_search_short_alias(self):
        response = await self.send_command('/sz geniusz')
        self.assert_message_hash_matches(response, expected_key="search_short_alias_geniusz.message")
