import pytest

from bot.database.database_manager import DatabaseManager
import bot.responses.administration.report_issue_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool", "test_client", "auth_token")
class TestReportIssueHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_report_with_valid_message(self):
        message = 'To i to nie działa'
        self.expect_command_result_contains(
            f'/report {message}',
            [msg.get_report_received_message()],
        )

    @pytest.mark.asyncio
    async def test_report_with_empty_message(self):
        command = '/report'
        self.expect_command_result_contains(
            command,
            [msg.get_no_report_content_message()],
        )

    @pytest.mark.asyncio
    async def test_report_with_special_characters_in_message(self):
        message = 'To się nie działa @#$%^&*()!'
        self.expect_command_result_contains(
            f'/report {message}',
            [msg.get_report_received_message()],
        )


    @pytest.mark.asyncio
    async def test_report_with_alias_command(self):
        message = 'Alias działa poprawnie'
        self.expect_command_result_contains(
            f'/r {message}',
            [msg.get_report_received_message()],
        )

    @pytest.mark.asyncio
    async def test_report_with_multiple_spaces(self):
        message = '   To się nie działa   '
        self.expect_command_result_contains(
            f'/report {message}',
            [msg.get_report_received_message()],
        )

    @pytest.mark.asyncio
    async def test_report_logs(self):
        message = 'To i to nie działa'

        self.expect_command_result_contains(
            f'/report {message}',
            [msg.get_report_received_message()],
        )

        reports = await DatabaseManager.get_reports(self.default_admin)

        assert len(reports) > 0, "Zgłoszenie nie zostało zapisane w bazie danych."
        assert reports[0]['report'] == message, f"Oczekiwano: {message}, otrzymano: {reports[0]['report']}"
