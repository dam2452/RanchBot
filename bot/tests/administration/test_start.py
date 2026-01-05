import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestStartHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_start_base_command(self):
        await self.expect_command_result_contains('/start', [await self.remove_n_lines(await self.get_response(RK.BASIC_MESSAGE),5)])

    @pytest.mark.asyncio
    async def test_start_invalid_command(self):
        await self.expect_command_result_contains(
            '/start', [await self.remove_n_lines(await self.get_response(RK.INVALID_COMMAND_MESSAGE),5)],
            args=['nieistniejace_polecenie']
        )

    async def test_start_list_command(self):
        await self.expect_command_result_contains('/start', [await self.remove_n_lines(await self.get_response(RK.LIST_MESSAGE),5)], args=['lista'])

    async def test_start_search_section(self):
        await self.expect_command_result_contains('/start', [await self.remove_n_lines(await self.get_response(RK.SEARCH_MESSAGE),5)], args=['wyszukiwanie'])

    async def test_start_edit_section(self):
        await self.expect_command_result_contains('/start', [await self.remove_n_lines(await self.get_response(RK.EDIT_MESSAGE),5)], args=['edycja'])

    async def test_start_management_section(self):
        await self.expect_command_result_contains('/start', [await self.remove_n_lines(await self.get_response(RK.MANAGEMENT_MESSAGE),5)], args=['zarzadzanie'])

    async def test_start_reporting_section(self):
        await self.expect_command_result_contains('/start', [await self.remove_n_lines(await self.get_response(RK.REPORTING_MESSAGE),5)], args=['raportowanie'])

    async def test_start_subscriptions_section(self):
        await self.expect_command_result_contains('/start', [await self.remove_n_lines(await self.get_response(RK.SUBSCRIPTIONS_MESSAGE),5)], args=['subskrypcje'])

    async def test_start_all_commands(self):
        await self.expect_command_result_contains('/start', [await self.remove_n_lines(await self.get_response(RK.ALL_MESSAGE),5)], args=['wszystko'])

    async def test_start_shortcuts(self):
        await self.expect_command_result_contains('/start', [await self.remove_n_lines(await self.get_response(RK.SHORTCUTS_MESSAGE),5)], args=['skroty'])
