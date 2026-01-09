import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestSearchListHandler(BaseTest):

    @pytest.mark.skip(reason="Needs to be fixed, throwing 500 as of now")
    @pytest.mark.asyncio
    async def test_list_after_successful_search(self):
        search_response = self.send_command('/szukaj krowa')
        self.assert_message_hash_matches(search_response, expected_key="search_krowa_results.message")

        list_response = self.send_command('/lista')
        self.assert_command_result_file_matches(list_response, 'list_krowa.txt')

    @pytest.mark.asyncio
    async def test_list_no_previous_search(self):
        response = self.send_command('/lista')
        self.assert_response_contains(response, [await self.get_response(RK.NO_PREVIOUS_SEARCH_RESULTS)])

    @pytest.mark.skip(reason="Needs to be fixed, throwing 500 as of now")
    @pytest.mark.asyncio
    async def test_list_with_special_characters_in_search(self):
        search_response = self.send_command('/szukaj "koń z chmurą"')
        self.assert_message_hash_matches(search_response, expected_key="search_kon_z_chmura_results.message")

        list_response = self.send_command('/lista')
        self.assert_command_result_file_matches(list_response, 'list_kon_z_chmura.txt')
