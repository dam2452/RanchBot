import logging
from typing import List

from bot.database import db
from bot.database.models import UserProfile
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.list_admins_handler_responses import (
    format_admins_list,
    get_log_admins_list_sent_message,
    get_log_no_admins_found_message,
    get_no_admins_found_message,
)


class ListAdminsHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["listadmins", "la"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    async def _do_handle(self) -> None:
        users = await db.get_admin_users()
        if not users:
            return await self.__reply_no_admins_found()

        response = format_admins_list(users)
        return await self.__reply_admins_list(response, users)

    async def __reply_no_admins_found(self) -> None:
        await self._reply(get_no_admins_found_message(), data={"admins": []})
        await self._log_system_message(logging.INFO, get_log_no_admins_found_message())

    async def __reply_admins_list(self, response: str, users: List[UserProfile]) -> None:
        await self._reply(response, data={"admins": [u.to_dict() for u in users]})
        await self._log_system_message(logging.INFO, get_log_admins_list_sent_message())
