from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)


class RemoveKeyHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["removekey", "rmk"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
        ]

    async def __check_argument_count(self) -> bool:
        usage_message = await self.get_response(RK.REMOVE_KEY_USAGE)
        return await self._validate_argument_count(self._message, 2, usage_message)

    async def _do_handle(self) -> None:
        args = self._message.get_text().split(maxsplit=1)
        if len(args) < 2:
            await self.reply_error(RK.REMOVE_KEY_USAGE)
            return

        key = args[1]
        success = await DatabaseManager.remove_subscription_key(key)

        if success:
            await self.reply(RK.REMOVE_KEY_SUCCESS, args=[key])
        else:
            await self.reply_error(RK.REMOVE_KEY_FAILURE, args=[key])
