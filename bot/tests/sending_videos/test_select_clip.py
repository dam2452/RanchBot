import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSelectClipHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_select_valid_segment(self):
        quote = "geniusz"
        await self.expect_command_result_hash(
            f'/szukaj {quote}',
            expected_key=f"search_{quote}_results.message",
        )

        select_response = await self.send_command('/wybierz 1')
        self.assert_command_result_file_matches(select_response, f'selected_{quote}_clip_1.mp4')

    @pytest.mark.asyncio
    async def test_select_no_previous_search(self):
        response = await self.send_command('/wybierz 1')
        await self.assert_response_contains(response, [await self.get_response(RK.NO_PREVIOUS_SEARCH)])

    @pytest.mark.asyncio
    async def test_select_invalid_segment_number(self):
        quote = "geniusz"
        await self.expect_command_result_hash(
            f'/szukaj {quote}',
            expected_key="search_geniusz_results.message",
        )

        response = await self.send_command('/wybierz 999')
        await self.assert_response_contains(response, [await self.get_response(RK.INVALID_SEGMENT_NUMBER)])
