import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.remove_subscription_handler_responses import get_log_subscription_removed_message


class RemoveSubscriptionHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["removesubscription", "rmsub"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_user_id_is_digit,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message,
            2,
            await self.get_response(RK.NO_USER_ID_PROVIDED),
        )

    async def __check_user_id_is_digit(self) -> bool:
        user_input = self._message.get_text().split()[1]
        if not user_input.isdigit():
            await self.__reply_invalid_user_id()
            return False
        return True

    async def _do_handle(self) -> None:
        user_id = int(self._message.get_text().split()[1])

        await DatabaseManager.remove_subscription(user_id)
        await self.__reply_subscription_removed(user_id)

    async def __reply_subscription_removed(self, user_id: int) -> None:
        await self._responder.send_text(
            await self.get_response(RK.SUBSCRIPTION_REMOVED, [str(user_id)]),
        )
        await self._log_system_message(
            logging.INFO,
            get_log_subscription_removed_message(str(user_id), self._message.get_username()),
        )

    async def __reply_invalid_user_id(self) -> None:
        await self._responder.send_text(await self.get_response(RK.NO_USER_ID_PROVIDED))
        await self._log_system_message(
            logging.WARNING,
            await self.get_response(RK.NO_USER_ID_PROVIDED),
        )
