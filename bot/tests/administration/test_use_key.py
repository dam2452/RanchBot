import pytest

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestSaveUserKeyHandler(BaseTest):

    @pytest.mark.quick
    def test_use_valid_key(self):
        key = "valid_key"
        subscription_days = 30

        DatabaseManager.create_subscription_key(subscription_days, key)
        self.expect_command_result_contains(
            f'/klucz {key}',
            [self.get_response(RK.SUBSCRIPTION_REDEEMED, [str(subscription_days)])],
        )
        self.expect_command_result_contains(
            f'/klucz {key}',
            [self.get_response(RK.INVALID_KEY)],
        )
        DatabaseManager.remove_subscription_key(key)

    @pytest.mark.quick
    def test_use_invalid_key(self):
        key = "invalid_key"

        response = self.send_command(f'/klucz {key}')
        self.assert_response_contains(response, [self.get_response(RK.INVALID_KEY)])

    @pytest.mark.quick
    def test_use_key_no_arguments(self):
        command = '/klucz'

        response = self.send_command(command)
        self.assert_response_contains(response, [self.get_response(RK.NO_KEY_PROVIDED)])

    @pytest.mark.long
    def test_use_key_special_characters(self):
        key = "spec!@#_key"
        subscription_days = 30

        DatabaseManager.create_subscription_key(subscription_days, key)
        self.expect_command_result_contains(
            f'/klucz {key}',
            [self.get_response(RK.SUBSCRIPTION_REDEEMED, [str(subscription_days)])],
        )
        self.expect_command_result_contains(
            f'/klucz {key}',
            [self.get_response(RK.INVALID_KEY)],
        )
        DatabaseManager.remove_subscription_key(key)

    @pytest.mark.long
    def test_use_key_multiple_times(self):
        key = "single_use_key"
        subscription_days = 30

        DatabaseManager.create_subscription_key(subscription_days, key)
        self.expect_command_result_contains(
            f'/klucz {key}',
            [self.get_response(RK.SUBSCRIPTION_REDEEMED, [str(subscription_days)])],
        )
        self.expect_command_result_contains(
            f'/klucz {key}',
            [self.get_response(RK.INVALID_KEY)],
        )
        DatabaseManager.remove_subscription_key(key)

    @pytest.mark.quick
    def test_use_key_edge_case(self):
        key = "key_" + "x" * 100
        subscription_days = 30

        DatabaseManager.create_subscription_key(subscription_days, key)
        self.expect_command_result_contains(
            f'/klucz {key}',
            [self.get_response(RK.SUBSCRIPTION_REDEEMED, [str(subscription_days)])],
        )
        self.expect_command_result_contains(
            f'/klucz {key}',
            [self.get_response(RK.INVALID_KEY)],
        )
        DatabaseManager.remove_subscription_key(key)
