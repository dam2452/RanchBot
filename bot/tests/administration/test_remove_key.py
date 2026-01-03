import pytest

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestRemoveKeyHandler(BaseTest):

    @pytest.mark.quick
    def test_remove_existing_key(self):
        key = "tajny_klucz"
        DatabaseManager.create_subscription_key(30, key)

        success_message = self.get_response(RK.REMOVE_KEY_SUCCESS, [key])
        self.expect_command_result_contains(f'/removekey {key}', [success_message])

    @pytest.mark.quick
    def test_remove_nonexistent_key(self):
        key = "nieistniejacy_klucz"

        failure_message = self.get_response(RK.REMOVE_KEY_FAILURE, [key])
        self.expect_command_result_contains(f'/removekey {key}', [failure_message])

    @pytest.mark.quick
    def test_remove_key_no_argument(self):
        usage_message = self.get_response(RK.REMOVE_KEY_USAGE)
        self.expect_command_result_contains('/removekey', [usage_message])

    @pytest.mark.long
    def test_remove_key_with_special_characters(self):
        key = "specjalny@klucz#!"
        DatabaseManager.create_subscription_key(30, key)
        self.expect_command_result_contains(
            f'/removekey {key}',
            [self.get_response(RK.REMOVE_KEY_SUCCESS, [key])],
        )

    @pytest.mark.long
    def test_remove_key_twice(self):
        key = "klucz_do_usuniecia"
        DatabaseManager.create_subscription_key(30, key)
        self.expect_command_result_contains(
            f'/removekey {key}',
            [self.get_response(RK.REMOVE_KEY_SUCCESS, [key])],
        )
        self.expect_command_result_contains(
            f'/removekey {key}',
            [self.get_response(RK.REMOVE_KEY_FAILURE, [key])],
        )
