import pytest

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest
from bot.tests.settings import settings as s


@pytest.mark.usefixtures("db_pool", "http_client", "auth_token")
class TestReportIssueHandler(BaseTest):

    @pytest.mark.quick
    @pytest.mark.asyncio
    async def test_report_with_valid_message(self):
        message = 'To i to nie działa'
        await self.expect_command_result_contains(f'/report {message}', [await self.get_response(RK.REPORT_RECEIVED)])

    @pytest.mark.quick
    @pytest.mark.asyncio
    async def test_report_with_empty_message(self):
        command = '/report'
        await self.expect_command_result_contains(command, [await self.get_response(RK.NO_REPORT_CONTENT)])

    @pytest.mark.quick
    @pytest.mark.asyncio
    async def test_report_with_special_characters_in_message(self):
        message = 'To się nie działa @#$%^&*()!'
        await self.expect_command_result_contains(f'/report {message}', [await self.get_response(RK.REPORT_RECEIVED)])


    @pytest.mark.quick
    @pytest.mark.asyncio
    async def test_report_with_alias_command(self):
        message = 'Alias działa poprawnie'
        await self.expect_command_result_contains(f'/r {message}', [await self.get_response(RK.REPORT_RECEIVED)])

    @pytest.mark.quick
    @pytest.mark.asyncio
    async def test_report_with_multiple_spaces(self):
        message = '   To się nie działa   '
        await self.expect_command_result_contains(f'/report {message}', [await self.get_response(RK.REPORT_RECEIVED)])

    @pytest.mark.quick
    @pytest.mark.asyncio
    async def test_report_logs(self):
        message = 'To i to nie działa'

        await self.expect_command_result_contains(f'/report {message}', [await self.get_response(RK.REPORT_RECEIVED)])

        reports = await DatabaseManager.get_reports(s.DEFAULT_ADMIN)

        assert len(reports) > 0, "Zgłoszenie nie zostało zapisane w bazie danych."
        assert reports[0]['report'] == message, f"Oczekiwano: {message}, otrzymano: {reports[0]['report']}"
