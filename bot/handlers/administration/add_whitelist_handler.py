import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.add_whitelist_handler_responses import (
    get_invalid_args_message,
    get_log_user_added_message,
    get_user_added_message,
)


class AddWhitelistHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["addwhitelist", "addw"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self._validate_user_id_is_digit,
        ]

    def _get_usage_message(self) -> str:
        return get_invalid_args_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1)

    async def _do_handle(self) -> None:
        user_input = self._message.get_text().split()[1]

        await DatabaseManager.add_user(
            user_id=int(user_input),
            username="",
            full_name="",
            note=None,
        )
        await self.__reply_user_added(user_input)

    async def __reply_user_added(self, user_input: str) -> None:
        await self._reply(get_user_added_message(user_input), data={"user_id": int(user_input)})
        await self._log_system_message(logging.INFO, get_log_user_added_message(user_input, self._message.get_username()))
