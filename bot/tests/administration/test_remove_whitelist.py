import pytest

import bot.responses.administration.remove_whitelist_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestRemoveWhitelistHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_remove_existing_user_whitelist(self):
        user = await self.add_test_user()
        self.expect_command_result_contains(
            f'/removewhitelist {user["user_id"]}',
            [msg.get_user_removed_message(str(user["user_id"]))],
        )


    @pytest.mark.asyncio
    async def test_remove_nonexistent_user_whitelist(self):
        user_id = 6967485026
        self.expect_command_result_contains(
            f'/removewhitelist {user_id}',
            [msg.get_user_not_in_whitelist_message(user_id)],
        )


    @pytest.mark.asyncio
    async def test_remove_user_whitelist_twice(self):
        user = await self.add_test_user()
        self.expect_command_result_contains(
            f'/removewhitelist {user["user_id"]}',
            [msg.get_user_removed_message(str(user["user_id"]))],
        )
        self.expect_command_result_contains(
            f'/removewhitelist {user["user_id"]}',
            [msg.get_user_not_in_whitelist_message(user["user_id"])],
        )

    @pytest.mark.asyncio
    async def test_remove_whitelist_invalid_user_id_format(self):
        self.expect_command_result_contains(
            '/removewhitelist user123',
            [msg.get_no_user_id_provided_message()],
        )
