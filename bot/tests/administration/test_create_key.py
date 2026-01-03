import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestCreateKeyHandler(BaseTest):

    @pytest.mark.quick
    def test_add_key_valid(self):
        key_name = "tajny_klucz"
        days = 30

        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [self.get_response(RK.CREATE_KEY_SUCCESS, [key_name, days])],
        )

    @pytest.mark.quick
    def test_add_key_zero_days(self):
        key_name = "klucz_na_zero_dni"
        days = 0

        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [self.get_response(RK.CREATE_KEY_USAGE)],
        )

    @pytest.mark.quick
    def test_add_key_negative_days(self):
        key_name = "klucz_na_ujemne_dni"
        days = -30

        self.send_command(f'/removekey {key_name}')
        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [self.get_response(RK.CREATE_KEY_USAGE)],
        )

    @pytest.mark.quick
    def test_add_key_invalid_days_format(self):
        invalid_days = "trzydzieści"
        key_name = "klucz_tekstowy_dni"

        self.expect_command_result_contains(
            f'/addkey {invalid_days} {key_name}',
            [self.get_response(RK.CREATE_KEY_USAGE)],
        )

    @pytest.mark.quick
    def test_add_key_empty_note(self):
        days = 30

        self.expect_command_result_contains(
            f'/addkey {days}',
            [self.get_response(RK.CREATE_KEY_USAGE)],
        )

    @pytest.mark.quick
    def test_add_key_special_characters_in_note(self):
        key_name = "specjalny@klucz#!"
        days = 30

        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [self.get_response(RK.CREATE_KEY_SUCCESS, [key_name, days])],
        )

    @pytest.mark.quick
    def test_add_key_duplicate(self):
        key_name = "duplikat_klucza"
        days = 30

        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [self.get_response(RK.CREATE_KEY_SUCCESS, [key_name, days])],
        )

        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [self.get_response(RK.KEY_ALREADY_EXISTS, [key_name])],
        )
