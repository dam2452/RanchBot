import logging
from typing import List

from bot.database import db
from bot.database.models import UserProfile
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.list_moderators_handler_responses import (
    format_moderators_list,
    get_log_moderators_list_sent_message,
    get_log_no_moderators_found_message,
    get_no_moderators_found_message,
)


class ListModeratorsHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["listmoderators", "lm"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    async def _do_handle(self) -> None:
        users = await db.get_moderator_users()
        if not users:
            return await self.__reply_no_moderators_found()

        response = format_moderators_list(users)
        return await self.__reply_moderators_list(response, users)

    async def __reply_no_moderators_found(self) -> None:
        await self._reply(get_no_moderators_found_message(), data={"moderators": []})
        await self._log_system_message(logging.INFO, get_log_no_moderators_found_message())

    async def __reply_moderators_list(self, response: str, users: List[UserProfile]) -> None:
        await self._reply(response, data={"moderators": [u.to_dict() for u in users]})
        await self._log_system_message(logging.INFO, get_log_moderators_list_sent_message())
