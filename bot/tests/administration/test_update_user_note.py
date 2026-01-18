import pytest

from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestUpdateUserNoteHandler(BaseTest):
    @pytest.mark.asyncio
    async def test_add_note_with_valid_user_and_content(self):
        user = await self.add_test_user()
        self.expect_command_result_contains(
            f'/note {user["user_id"]} notatka123',
            [await self.get_response(RK.NOTE_UPDATED)],
        )

    @pytest.mark.asyncio
    async def test_note_missing_user_id_and_content(self):
        response = self.send_command('/note')
        self.assert_response_contains(response, [await self.get_response(RK.NO_NOTE_PROVIDED)])

    @pytest.mark.asyncio
    async def test_note_missing_content(self):
        user = await self.add_test_user()
        response = self.send_command(f'/note {user["user_id"]}')
        self.assert_response_contains(response, [await self.get_response(RK.NO_NOTE_PROVIDED)])

    @pytest.mark.asyncio
    async def test_note_with_special_characters_in_content(self):
        user = await self.add_test_user()
        self.expect_command_result_contains(
            f'/note {user["user_id"]} notatka@#!$%&*()',
            [await self.get_response(RK.NOTE_UPDATED)],
        )

    @pytest.mark.asyncio
    async def test_note_with_invalid_user_id_format(self):
        user = "user123"
        response = self.send_command(f'/note {user} notatka_testowa')
        self.assert_response_contains(response, [await self.get_response(RK.INVALID_USER_ID, [user])])

    @pytest.mark.asyncio
    async def test_note_with_long_content(self):
        user = await self.add_test_user()
        long_content = "to jest bardzo długa notatka " * 20
        self.expect_command_result_contains(
            f'/note {user["user_id"]} {long_content}',
            [await self.get_response(RK.NOTE_UPDATED)],
        )

    @pytest.mark.asyncio
    async def test_update_existing_note(self):
        user = await self.add_test_user()
        self.expect_command_result_contains(
            f'/note {user["user_id"]} pierwsza_notatka',
            [await self.get_response(RK.NOTE_UPDATED)],
        )
        self.expect_command_result_contains(
            f'/note {user["user_id"]} druga_notatka',
            [await self.get_response(RK.NOTE_UPDATED)],
        )
