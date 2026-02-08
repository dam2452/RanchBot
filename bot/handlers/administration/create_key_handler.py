import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.create_key_handler_responses import (
    get_create_key_success_message,
    get_create_key_usage_message,
    get_key_already_exists_message,
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
        return await self._validate_argument_count(self._message, 2, get_create_key_usage_message())

    async def __check_days_is_digit(self) -> bool:
        args = self._message.get_text().split()
        try:
            if int(args[1]) <= 0:
                raise ValueError()
        except (IndexError, ValueError):
            await self._reply_error(get_create_key_usage_message())
            await self._log_system_message(logging.INFO, get_create_key_usage_message())
            return False
        return True

    async def __check_key_is_unique(self) -> bool:
        args = self._message.get_text().split()
        key = " ".join(args[2:])
        if await DatabaseManager.get_subscription_days_by_key(key):
            await self._reply_error(get_key_already_exists_message(key))
            await self._log_system_message(logging.INFO, get_key_already_exists_message(key))
            return False
        return True

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        days = int(args[1])
        key = " ".join(args[2:])

        await DatabaseManager.create_subscription_key(days, key)

        await self._reply(
            get_create_key_success_message(days, key),
            data={"days": days, "key": key},
        )
        await self._log_system_message(logging.INFO, get_create_key_success_message(days, key))
