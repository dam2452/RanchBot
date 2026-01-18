import pytest

from bot.database.database_manager import DatabaseManager
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestRemoveKeyHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_remove_existing_key(self):
        key = "tajny_klucz"
        await DatabaseManager.create_subscription_key(30, key)

        success_message = await self.get_response(RK.REMOVE_KEY_SUCCESS, [key])
        self.expect_command_result_contains(f'/removekey {key}', [success_message])

    @pytest.mark.asyncio
    async def test_remove_nonexistent_key(self):
        key = "nieistniejacy_klucz"

        failure_message = await self.get_response(RK.REMOVE_KEY_FAILURE, [key])
        self.expect_command_result_contains(f'/removekey {key}', [failure_message])

    @pytest.mark.asyncio
    async def test_remove_key_no_argument(self):
        usage_message = await self.get_response(RK.REMOVE_KEY_USAGE)
        self.expect_command_result_contains('/removekey', [usage_message])

    @pytest.mark.asyncio
    async def test_remove_key_with_special_characters(self):
        key = "specjalny@klucz#!"
        await DatabaseManager.create_subscription_key(30, key)
        self.expect_command_result_contains(
            f'/removekey {key}',
            [await self.get_response(RK.REMOVE_KEY_SUCCESS, [key])],
        )

    @pytest.mark.asyncio
    async def test_remove_key_twice(self):
        key = "klucz_do_usuniecia"
        await DatabaseManager.create_subscription_key(30, key)
        self.expect_command_result_contains(
            f'/removekey {key}',
            [await self.get_response(RK.REMOVE_KEY_SUCCESS, [key])],
        )
        self.expect_command_result_contains(
            f'/removekey {key}',
            [await self.get_response(RK.REMOVE_KEY_FAILURE, [key])],
        )
