import logging
from typing import List

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.admin_help_handler_responses import (
    get_admin_help_message,
    get_admin_shortcuts_message,
    get_message_sent_log_message,
    get_shortcuts_sent_log_message,
)


class AdminHelpHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["admin"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    async def _do_handle(self) -> None:
        keywords = ["skroty", "skróty", "skrot", "skrót"]
        if any(keyword in self._message.get_text().lower() for keyword in keywords):
            await self.__reply_admin_shortcuts()
        else:
            await self.__reply_admin_help()

    async def __reply_admin_help(self) -> None:
        await self._reply(get_admin_help_message(), data={"markdown": get_admin_help_message()})

        await self._log_system_message(logging.INFO, get_message_sent_log_message(self._message.get_username()))

    async def __reply_admin_shortcuts(self) -> None:
        await self._reply(get_admin_shortcuts_message(), data={"markdown": get_admin_shortcuts_message()})
        await self._log_system_message(logging.INFO, get_shortcuts_sent_log_message(self._message.get_username()))
