import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.create_key_handler_responses import (
    get_key_added_message,
    get_log_key_name_exists_message,
    get_wrong_argument_message,
)


class CreateKeyHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["addkey", "addk"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_days_is_digit,
            self.__check_key_is_unique,
        ]

    async def __check_argument_count(self) -> bool:
        if not await self._validate_argument_count(
                self._message, 3, await self.get_response(RK.CREATE_KEY_USAGE),
        ):
            await self.reply_error(RK.CREATE_KEY_USAGE)
            return False
        return True

    async def __check_days_is_digit(self) -> bool:
        args = self._message.get_text().split()
        if not args[1].isdigit():
            await self.reply_error(RK.CREATE_KEY_USAGE)
            await self._log_system_message(logging.INFO, get_wrong_argument_message())
            return False
        return True

    async def __check_key_is_unique(self) -> bool:
        args = self._message.get_text().split()
        key = " ".join(args[2:])
        if await DatabaseManager.get_subscription_days_by_key(key):
            await self.reply_error(RK.KEY_ALREADY_EXISTS, args=[key])
            await self._log_system_message(logging.INFO, get_log_key_name_exists_message(key))
            return False
        return True

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        days = int(args[1])
        key = " ".join(args[2:])

        await DatabaseManager.create_subscription_key(days, key)

        await self.reply(
            RK.CREATE_KEY_SUCCESS,
            args=[key, days],
            data={"days": days, "key": key},
        )
        await self._log_system_message(logging.INFO, get_key_added_message(key, days))
