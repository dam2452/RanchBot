import pytest

import bot.responses.filter_command_messages as filter_msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSearchFilterHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_search_filter_no_active_filter(self):
        self.send_command('/filtr reset')
        response = self.send_command('/szukajfiltr')
        self.assert_response_contains(response, [filter_msg.get_no_filter_set_message()])

    @pytest.mark.asyncio
    async def test_search_filter_alias_szf_no_active_filter(self):
        self.send_command('/filtr reset')
        response = self.send_command('/szf')
        self.assert_response_contains(response, [filter_msg.get_no_filter_set_message()])

    @pytest.mark.asyncio
    async def test_search_filter_with_active_filter(self):
        self.send_command('/filtr reset')
        self.send_command('/filtr sezon:1')
        await self.expect_command_result_hash(
            '/szukajfiltr',
            expected_key="search_filter_sezon1.message",
        )

    @pytest.mark.asyncio
    async def test_search_filter_with_quote(self):
        self.send_command('/filtr reset')
        self.send_command('/filtr sezon:1')
        await self.expect_command_result_hash(
            '/szukajfiltr geniusz',
            expected_key="search_filter_sezon1_geniusz.message",
        )

    @pytest.mark.asyncio
    async def test_search_filter_no_matching_segments(self):
        self.send_command('/filtr reset')
        self.send_command('/filtr sezon:99')
        response = self.send_command('/szukajfiltr')
        self.assert_response_contains(response, [filter_msg.get_no_segments_match_active_filter_message()])
