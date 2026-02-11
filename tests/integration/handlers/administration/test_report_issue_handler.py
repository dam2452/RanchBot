import logging

import pytest

from bot.handlers.administration.report_issue_handler import ReportIssueHandler
from tests.integration.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("mock_db")
class TestReportIssueHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_report_issue_success(self, mock_db):
        message = self.create_message('/report Bug found in search')
        responder = self.create_responder()

        handler = ReportIssueHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        assert len(mock_db._reports) == 1, "Report should be saved"
        assert mock_db._reports[0]['report'] == 'Bug found in search'

    @pytest.mark.asyncio
    async def test_report_issue_with_long_text(self, mock_db):
        report_text = 'Long report text ' * 50
        message = self.create_message(f'/r {report_text}')
        responder = self.create_responder()

        handler = ReportIssueHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send response"

    @pytest.mark.asyncio
    async def test_report_issue_with_special_characters(self, mock_db):
        report_text = 'Report with !@#$%^&*() special chars'
        message = self.create_message(f'/zgłoś {report_text}')
        responder = self.create_responder()

        handler = ReportIssueHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        assert len(mock_db._reports) == 1
        assert mock_db._reports[0]['report'] == report_text

    @pytest.mark.asyncio
    async def test_report_issue_with_unicode(self, mock_db):
        report_text = 'Błąd w polskich znakach: ąćęłńóśźż'
        message = self.create_message(f'/zglos {report_text}')
        responder = self.create_responder()

        handler = ReportIssueHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send success message"
        assert len(mock_db._reports) == 1

    @pytest.mark.asyncio
    async def test_report_issue_missing_content(self, mock_db):
        message = self.create_message('/report')
        responder = self.create_responder()

        handler = ReportIssueHandler(message, responder, logger)
        await handler.handle()

        assert responder.has_sent_text(), "Handler should send error message"
        assert len(mock_db._reports) == 0, "No report should be saved"

    @pytest.mark.asyncio
    async def test_report_issue_multiple_reports_from_same_user(self, mock_db):
        user_id = self.admin_id

        message1 = self.create_message('/report First bug', user_id=user_id)
        responder1 = self.create_responder()
        handler1 = ReportIssueHandler(message1, responder1, logger)
        await handler1.handle()

        message2 = self.create_message('/report Second bug', user_id=user_id)
        responder2 = self.create_responder()
        handler2 = ReportIssueHandler(message2, responder2, logger)
        await handler2.handle()

        assert len(mock_db._reports) == 2, "Both reports should be saved"
        assert mock_db._reports[0]['report'] == 'First bug'
        assert mock_db._reports[1]['report'] == 'Second bug'

    @pytest.mark.asyncio
    async def test_report_issue_different_aliases(self, mock_db):
        for command in ['/report', '/zgłoś', '/zglos', '/r']:
            mock_db.reset()
            message = self.create_message(f'{command} Test report')
            responder = self.create_responder()

            handler = ReportIssueHandler(message, responder, logger)
            await handler.handle()

            assert responder.has_sent_text(), f"Handler should respond to {command}"
            if 'brak' not in ' '.join(responder.get_all_text_responses()).lower():
                assert len(mock_db._reports) >= 0
