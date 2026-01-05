import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestAdminHelpHandler(BaseTest):

    @pytest.mark.quick
    async def test_admin_help(self):
        await self.expect_command_result_contains(
            '/admin',
            [await self.remove_first_line(await self.get_response(RK.ADMIN_HELP))],
        )

    @pytest.mark.quick
    async def test_admin_shortcuts(self):
        await self.expect_command_result_contains(
            '/admin',
            [await self.remove_first_line(await self.get_response(RK.ADMIN_SHORTCUTS))],
            args=['skroty']
        )

    async def test_admin_invalid_command(self):
        await self.expect_command_result_contains(
            '/admin',
            [await self.remove_first_line(await self.get_response(RK.ADMIN_HELP))],
            args=['nieistniejace_polecenie']
        )
