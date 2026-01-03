import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestUpdateUserNoteHandler(BaseTest):

    def test_add_note_with_valid_user_and_content(self):
        user = self.add_test_user()
        self.expect_command_result_contains(
            f'/note {user["user_id"]} notatka123',
            [self.get_response(RK.NOTE_UPDATED)],
        )

    def test_note_missing_user_id_and_content(self):
        response = self.send_command('/note')
        self.assert_response_contains(response, [self.get_response(RK.NO_NOTE_PROVIDED)])

    def test_note_missing_content(self):
        user = self.add_test_user()
        response = self.send_command(f'/note {user["user_id"]}')
        self.assert_response_contains(response, [self.get_response(RK.NO_NOTE_PROVIDED)])

    def test_note_with_special_characters_in_content(self):
        user = self.add_test_user()
        self.expect_command_result_contains(
            f'/note {user["user_id"]} notatka@#!$%&*()',
            [self.get_response(RK.NOTE_UPDATED)],
        )

    def test_note_with_invalid_user_id_format(self):
        user = "user123"
        response = self.send_command(f'/note {user} notatka_testowa')
        self.assert_response_contains(response, [self.get_response(RK.INVALID_USER_ID, [user])])

    def test_note_with_long_content(self):
        user = self.add_test_user()
        long_content = "to jest bardzo długa notatka " * 20
        self.expect_command_result_contains(
            f'/note {user["user_id"]} {long_content}',
            [self.get_response(RK.NOTE_UPDATED)],
        )

    def test_update_existing_note(self):
        user = self.add_test_user()
        self.expect_command_result_contains(
            f'/note {user["user_id"]} pierwsza_notatka',
            [self.get_response(RK.NOTE_UPDATED)],
        )
        self.expect_command_result_contains(
            f'/note {user["user_id"]} druga_notatka',
            [self.get_response(RK.NOTE_UPDATED)],
        )
