import pytest

from bot.database.database_manager import DatabaseManager
import bot.responses.administration.account_code_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestAccountCodeHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_account_code_generated(self):
        await DatabaseManager.remove_credentials(self.default_admin)
        response = self.send_command('/kodkonta')
        self.assert_response_contains(response, ["KOD REJESTRACJI"])

    @pytest.mark.asyncio
    async def test_account_code_alias(self):
        await DatabaseManager.remove_credentials(self.default_admin)
        response = self.send_command('/accountcode')
        self.assert_response_contains(response, ["KOD REJESTRACJI"])

    @pytest.mark.asyncio
    async def test_account_code_already_has_credentials(self):
        response = self.send_command('/kodkonta')
        self.assert_response_contains(response, [msg.get_already_has_credentials_message()])
