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
        return await self.__reply_whitelist(response, users)

    async def __reply_whitelist_empty(self) -> None:
        await self._reply(get_whitelist_empty_message(), data={"whitelist": []})
        await self._log_system_message(logging.INFO, get_log_whitelist_empty_message())

    async def __reply_whitelist(self, response: str, users: List[UserProfile]) -> None:
        await self._reply(response, data={"whitelist": [u.to_dict() for u in users]})
        await self._log_system_message(logging.INFO, get_log_whitelist_sent_message())
