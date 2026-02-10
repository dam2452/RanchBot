import pytest

import bot.responses.administration.create_key_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestCreateKeyHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_add_key_valid(self):
        key_name = "tajny_klucz"
        days = 30

        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [msg.get_create_key_success_message(days, key_name)],
        )

    @pytest.mark.asyncio
    async def test_add_key_zero_days(self):
        key_name = "klucz_na_zero_dni"
        days = 0

        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [msg.get_create_key_usage_message()],
        )

    @pytest.mark.asyncio
    async def test_add_key_negative_days(self):
        key_name = "klucz_na_ujemne_dni"
        days = -30

        self.send_command(f'/removekey {key_name}')
        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [msg.get_create_key_usage_message()],
        )

    @pytest.mark.asyncio
    async def test_add_key_invalid_days_format(self):
        invalid_days = "trzydzieści"
        key_name = "klucz_tekstowy_dni"

        self.expect_command_result_contains(
            f'/addkey {invalid_days} {key_name}',
            [msg.get_create_key_usage_message()],
        )

    @pytest.mark.asyncio
    async def test_add_key_special_characters_in_note(self):
        key_name = "specjalny@klucz#!"
        days = 30

        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [msg.get_create_key_success_message(days, key_name)],
        )

    @pytest.mark.asyncio
    async def test_add_key_duplicate(self):
        key_name = "duplikat_klucza"
        days = 30

        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [msg.get_create_key_success_message(days, key_name)],
        )

        self.expect_command_result_contains(
            f'/addkey {days} {key_name}',
            [msg.get_key_already_exists_message(key_name)],
        )
