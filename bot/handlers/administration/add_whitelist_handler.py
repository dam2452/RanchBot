import logging
from typing import List

from bot.database import db
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.add_whitelist_handler_responses import (
    get_log_user_added_message,
    get_no_user_id_provided_message,
    get_no_username_provided_message,
    get_user_added_message,
)


class AddWhitelistHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["addwhitelist", "addw"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_user_id_is_digit,
        ]

    async def __check_argument_count(self) -> bool:
        if not await self._validate_argument_count(
            self._message, 1, get_no_username_provided_message(),
        ):
            await self.__reply_user_not_found()
            return False
        return True

    async def __check_user_id_is_digit(self) -> bool:
        user_input = self._message.get_text().split()[1]
        if not user_input.isdigit():
            await self.__reply_user_not_found()
            return False
        return True

    async def _do_handle(self) -> None:
        user_input = self._message.get_text().split()[1]

        await db.add_user(
            user_id=int(user_input),
            username="",
            full_name="",
            note=None,
        )
        await self.__reply_user_added(user_input)

    async def __reply_user_added(self, user_input: str) -> None:
        await self._reply(get_user_added_message(user_input), data={"user_id": int(user_input)})
        await self._log_system_message(logging.INFO, get_log_user_added_message(user_input, self._message.get_username()))

    async def __reply_user_not_found(self) -> None:
        await self._reply(get_no_user_id_provided_message())
        await self._log_system_message(logging.INFO, get_no_user_id_provided_message())
