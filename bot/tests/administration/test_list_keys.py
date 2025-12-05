import pytest

from bot.database.database_manager import DatabaseManager
import bot.responses.administration.list_keys_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "http_client", "auth_token")
class TestListKeysCommand(BaseTest):

    @pytest.mark.quick
    @pytest.mark.asyncio
    async def test_list_keys_with_keys(self):
        await DatabaseManager.create_subscription_key(30, "key1")
        await DatabaseManager.create_subscription_key(60, "key2")

        keys = await DatabaseManager.get_all_subscription_keys()

        await self.expect_command_result_contains(
            '/listkey',
            [msg.create_subscription_keys_response(keys)],
        )

    @pytest.mark.quick
    @pytest.mark.asyncio
    async def test_list_keys_empty(self):
        await self.expect_command_result_contains(
            '/listkey',
            [msg.get_subscription_keys_empty_message()],
        )
