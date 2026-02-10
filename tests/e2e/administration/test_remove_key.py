import pytest

from bot.database.database_manager import DatabaseManager
import bot.responses.administration.remove_key_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestRemoveKeyHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_remove_existing_key(self):
        key = "tajny_klucz"
        await DatabaseManager.create_subscription_key(30, key)

        self.expect_command_result_contains(
            f'/removekey {key}',
            [msg.get_remove_key_success_message(key)],
        )

    @pytest.mark.asyncio
    async def test_remove_nonexistent_key(self):
        key = "nieistniejacy_klucz"

        self.expect_command_result_contains(
            f'/removekey {key}',
            [msg.get_remove_key_failure_message(key)],
        )

    @pytest.mark.asyncio
    async def test_remove_key_no_argument(self):
        self.expect_command_result_contains(
            '/removekey',
            [msg.get_remove_key_usage_message()],
        )

    @pytest.mark.asyncio
    async def test_remove_key_with_special_characters(self):
        key = "specjalny@klucz#!"
        await DatabaseManager.create_subscription_key(30, key)
        self.expect_command_result_contains(
            f'/removekey {key}',
            [msg.get_remove_key_success_message(key)],
        )

    @pytest.mark.asyncio
    async def test_remove_key_twice(self):
        key = "klucz_do_usuniecia"
        await DatabaseManager.create_subscription_key(30, key)
        self.expect_command_result_contains(
            f'/removekey {key}',
            [msg.get_remove_key_success_message(key)],
        )
        self.expect_command_result_contains(
            f'/removekey {key}',
            [msg.get_remove_key_failure_message(key)],
        )
