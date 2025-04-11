import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.models import UserProfile
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.list_whitelist_handler_responses import (
    create_whitelist_response,
    get_log_whitelist_empty_message,
    get_log_whitelist_sent_message,
    get_whitelist_empty_message,
)


class ListWhitelistHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["listwhitelist", "lw"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    async def _do_handle(self) -> None:
        users = await DatabaseManager.get_all_users()
        if not users:
            return await self.__reply_whitelist_empty()

        response = create_whitelist_response(users)
        await self.__reply_whitelist(response, users)

    async def __reply_whitelist_empty(self) -> None:
        if self._message.get_json_flag():
            await self.reply(
                key="",
                data={"whitelist": []},
            )
        else:
            await self._responder.send_text(get_whitelist_empty_message())

        await self._log_system_message(logging.INFO, get_log_whitelist_empty_message())

    async def __reply_whitelist(self, response: str, users: List[UserProfile]) -> None:
        if self._message.get_json_flag():
            await self.reply(
                key="",
                data={"whitelist": [u.to_dict() for u in users]},
            )
        else:
            await self._responder.send_markdown(response)

        await self._log_system_message(logging.INFO, get_log_whitelist_sent_message())
