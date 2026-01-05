import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestAddWhitelistHandler(BaseTest):
    @pytest.mark.quick
    async def test_add_and_remove_valid_user_whitelist(self):
        user_id = 123456789
        await self.get_response(
            user_id=user_id,
            username="valid_user",
            full_name="Valid User",
            note=None,
            subscription_days=None,
        )

        expected_add_message = await self.get_response(RK.USER_ADDED, [str(user_id)])
        await self.expect_command_result_contains(
            f'/addwhitelist {user_id}',
            [expected_add_message],
        )

    @pytest.mark.quick
    async def test_add_nonexistent_user_whitelist(self):
        user_id = 99999999999
        await self.expect_command_result_contains(
            f'/addwhitelist {user_id}',
            [await self.get_response(RK.USER_ADDED, [str(user_id)])],
        )

    async def test_add_whitelist_invalid_user_id_format(self):
        user_id_invalid = "invalid_id"
        expected_message = await self.get_response(RK.NO_USER_ID_PROVIDED)

        await self.expect_command_result_contains(
            f'/addwhitelist {user_id_invalid}',
            [expected_message],
        )

    async def test_add_user_with_no_username(self):
        user_id = 888888888
        await self.get_response(
            user_id=user_id,
            username=None,
            full_name="",
            note=None,
            subscription_days=None,
        )

        await self.expect_command_result_contains(
            f'/addwhitelist {user_id}',
            [await self.get_response(RK.USER_ADDED, [str(user_id)])],
        )
