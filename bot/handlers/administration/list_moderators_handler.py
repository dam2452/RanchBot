import logging
from typing import List

from bot.database.database_manager import DatabaseManager
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
        users = await DatabaseManager.get_moderator_users()
        if not users:
            return await self.__reply_no_moderators_found()

        response = format_moderators_list(users)
        return await self.__reply_moderators_list(response, users)

    async def __reply_no_moderators_found(self) -> None:
        message = get_no_moderators_found_message()

        if self._message.should_reply_json():
            await self.reply("", data={"moderators": []})
        else:
            await self._responder.send_text(message)

        await self._log_system_message(logging.INFO, get_log_no_moderators_found_message())

    async def __reply_moderators_list(self, response: str, users: List[UserProfile]) -> None:
        if self._message.should_reply_json():
            await self.reply("", data={"moderators": [u.to_dict() for u in users]})
        else:
            await self._responder.send_markdown(response)

        await self._log_system_message(logging.INFO, get_log_moderators_list_sent_message())
