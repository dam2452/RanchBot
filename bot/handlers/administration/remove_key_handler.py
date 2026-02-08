from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.remove_key_handler_responses import (
    get_remove_key_failure_message,
    get_remove_key_success_message,
    get_remove_key_usage_message,
)


class RemoveKeyHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["removekey", "rmk"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_remove_key_usage_message())

    async def _do_handle(self) -> None:
        args = self._message.get_text().split(maxsplit=1)
        key = args[1]
        success = await DatabaseManager.remove_subscription_key(key)

        if success:
            await self._reply(get_remove_key_success_message(key))
        else:
            await self._reply_error(get_remove_key_failure_message(key))
