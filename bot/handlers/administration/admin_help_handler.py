import logging
from typing import List

from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.admin_help_handler_responses import get_message_sent_log_message


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
        response = await self.get_response(RK.ADMIN_HELP)
        if self._message.should_reply_json():
            await self.reply(RK.ADMIN_HELP, data={"markdown": response})
        else:
            await self._responder.send_markdown(response)

        await self._log_system_message(
            logging.INFO,
            get_message_sent_log_message(self._message.get_username()),
        )

    async def __reply_admin_shortcuts(self) -> None:
        response = await self.get_response(RK.ADMIN_SHORTCUTS)
        if self._message.should_reply_json():
            await self.reply(RK.ADMIN_SHORTCUTS, data={"markdown": response})
        else:
            await self._responder.send_markdown(response)

        await self._log_system_message(
            logging.INFO,
            f"Admin shortcuts sent to {self._message.get_username()}",
        )
