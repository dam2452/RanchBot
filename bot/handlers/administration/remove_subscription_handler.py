import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.remove_subscription_handler_responses import (
    get_log_subscription_removed_message,
    get_no_user_id_provided_message,
    get_subscription_removed_message,
)


class RemoveSubscriptionHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["removesubscription", "rmsub"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_user_id_is_digit,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_no_user_id_provided_message())

    async def __check_user_id_is_digit(self) -> bool:
        user_input = self._message.get_text().split()[1]
        if not user_input.isdigit():
            await self.reply_error(get_no_user_id_provided_message())
            return False
        return True

    async def _do_handle(self) -> None:
        user_id = int(self._message.get_text().split()[1])

        await DatabaseManager.remove_subscription(user_id)

        await self.reply(get_subscription_removed_message(str(user_id)))
        await self._log_system_message(logging.INFO, get_log_subscription_removed_message(str(user_id), self._message.get_username()))
