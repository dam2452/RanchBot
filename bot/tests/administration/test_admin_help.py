import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "http_client", "auth_token")
class TestAdminHelpHandler(BaseTest):

    @pytest.mark.quick
    @pytest.mark.asyncio
    async def test_admin_help(self):
        await self.expect_command_result_contains(
            '/admin',
            [self.remove_first_line(await self.get_response(RK.ADMIN_HELP))],
        )

    @pytest.mark.quick
    @pytest.mark.asyncio
    async def test_admin_shortcuts(self):
        await self.expect_command_result_contains(
            '/admin',
            [self.remove_first_line(await self.get_response(RK.ADMIN_SHORTCUTS))],
            args=['skroty']
        )

    @pytest.mark.asyncio
    async def test_admin_invalid_command(self):
        await self.expect_command_result_contains(
            '/admin',
            [self.remove_first_line(await self.get_response(RK.ADMIN_HELP))],
            args=['nieistniejace_polecenie']
        )
