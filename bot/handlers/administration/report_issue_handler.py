import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.report_issue_handler_responses import get_log_report_received_message
from bot.settings import settings


class ReportIssueHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["report", "zgłoś", "zglos", "r"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_report_length,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message,
            2,
            await self.get_response(RK.NO_REPORT_CONTENT),
        )

    async def __check_report_length(self) -> bool:
        report_content = self._message.get_text().split(maxsplit=1)[1]
        if len(report_content) > settings.MAX_REPORT_LENGTH:
            await self.reply_error(RK.LIMIT_EXCEEDED_REPORT_LENGTH)
            return False
        return True

    async def _do_handle(self) -> None:
        report_content = self._message.get_text().split(maxsplit=1)[1]
        await self.__handle_user_report_submission(report_content)

    async def __handle_user_report_submission(self, report: str) -> None:
        await DatabaseManager.add_report(self._message.get_user_id(), report)
        await self.reply(RK.REPORT_RECEIVED)
        await self._log_system_message(
            logging.INFO,
            get_log_report_received_message(self._message.get_username(), report),
        )
