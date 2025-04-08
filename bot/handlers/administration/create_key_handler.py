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
        return await self._validate_argument_count(
            self._message,
            3,
            await self.get_response(RK.CREATE_KEY_USAGE),
        )

    async def __check_days_is_digit(self) -> bool:
        args = self._message.get_text().split()
        if not args[1].isdigit():
            await self.__reply_wrong_argument()
            return False
        return True

    async def __check_key_is_unique(self) -> bool:
        args = self._message.get_text().split()
        key = " ".join(args[2:])
        key_exists = await DatabaseManager.get_subscription_days_by_key(key)
        if key_exists is not None:
            await self.__reply_key_already_exists(key)
            return False
        return True

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        days = int(args[1])
        key = " ".join(args[2:])

        await DatabaseManager.create_subscription_key(days, key)
        await self.__reply_key_added(days, key)

    async def __reply_key_added(self, days: int, key: str) -> None:
        await self._responder.send_text(
            await self.get_response(RK.CREATE_KEY_SUCCESS, [key, days]),
        )
        await self._log_system_message(
            logging.INFO, get_key_added_message(key, days),
        )

    async def __reply_wrong_argument(self) -> None:
        await self._responder.send_text(await self.get_response(RK.CREATE_KEY_USAGE))
        await self._log_system_message(logging.INFO, get_wrong_argument_message())

    async def __reply_key_already_exists(self, key: str) -> None:
        await self._responder.send_text(
            await self.get_response(RK.KEY_ALREADY_EXISTS, [key]),
        )
        await self._log_system_message(logging.INFO, get_log_key_name_exists_message(key))
