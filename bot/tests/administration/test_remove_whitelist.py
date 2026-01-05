import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestRemoveWhitelistHandler(BaseTest):

    @pytest.mark.quick
    async def test_remove_existing_user_whitelist(self):
        user = await self.add_test_user()
        await self.expect_command_result_contains(
            f'/removewhitelist {user["user_id"]}',
            [await self.get_response(RK.USER_REMOVED, [str(user["user_id"])])],
        )


    @pytest.mark.quick
    async def test_remove_nonexistent_user_whitelist(self):
        user_id = 6967485026
        await self.expect_command_result_contains(
            f'/removewhitelist {user_id}',
            [await self.get_response(RK.USER_NOT_IN_WHITELIST, [str(user_id)])],
        )


    @pytest.mark.long
    async def test_remove_user_whitelist_twice(self):
        user = await self.add_test_user()
        await self.expect_command_result_contains(
            f'/removewhitelist {user["user_id"]}',
            [await self.get_response(RK.USER_REMOVED, [str(user["user_id"])])],
        )
        await self.expect_command_result_contains(
            f'/removewhitelist {user["user_id"]}',
            [await self.get_response(RK.USER_NOT_IN_WHITELIST,[str(user["user_id"])])],
        )

    @pytest.mark.quick
    async def test_remove_whitelist_invalid_user_id_format(self):
        await self.expect_command_result_contains(
            '/removewhitelist user123',
            [await self.get_response(RK.NO_USER_ID_PROVIDED)],
        )
