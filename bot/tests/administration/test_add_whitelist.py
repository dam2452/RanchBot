import pytest

from bot.database.database_manager import DatabaseManager
import bot.responses.administration.add_whitelist_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestAddWhitelistHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_add_and_remove_valid_user_whitelist(self):
        user_id = 123456789
        await DatabaseManager.add_user(
            user_id=user_id,
            username="valid_user",
            full_name="Valid User",
            note=None,
            subscription_days=None,
        )

        self.expect_command_result_contains(
            f'/addwhitelist {user_id}',
            [msg.get_user_added_message(str(user_id))],
        )

    @pytest.mark.asyncio
    async def test_add_nonexistent_user_whitelist(self):
        user_id = 99999999999
        self.expect_command_result_contains(
            f'/addwhitelist {user_id}',
            [msg.get_user_added_message(str(user_id))],
        )

    @pytest.mark.asyncio
    async def test_add_whitelist_invalid_user_id_format(self):
        user_id_invalid = "invalid_id"

        self.expect_command_result_contains(
            f'/addwhitelist {user_id_invalid}',
            [msg.get_no_user_id_provided_message()],
        )

    @pytest.mark.asyncio
    async def test_add_user_with_no_username(self):
        user_id = 888888888
        await DatabaseManager.add_user(
            user_id=user_id,
            username=None,
            full_name="",
            note=None,
            subscription_days=None,
        )

        self.expect_command_result_contains(
            f'/addwhitelist {user_id}',
            [msg.get_user_added_message(str(user_id))],
        )
