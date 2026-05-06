import pytest

from bot.database.database_manager import DatabaseManager
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestAccountCodeHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_account_code_registration(self):
        await DatabaseManager.remove_credentials(self.default_admin)
        response = self.send_command('/kodkonta')
        self.assert_response_contains(response, ["KOD REJESTRACJI"])

    @pytest.mark.asyncio
    async def test_account_code_alias(self):
        await DatabaseManager.remove_credentials(self.default_admin)
        response = self.send_command('/accountcode')
        self.assert_response_contains(response, ["KOD REJESTRACJI"])

    @pytest.mark.asyncio
    async def test_account_code_password_reset(self):
        response = self.send_command('/kodkonta')
        self.assert_response_contains(response, ["KOD RESETU HASLA"])
