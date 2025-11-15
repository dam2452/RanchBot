from datetime import date
import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.add_subscription_handler_responses import (
    get_subscription_error_log_message,
    get_subscription_log_message,
)


class AddSubscriptionHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["addsubscription", "addsub"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__validate_user_id_and_days,
        ]

    async def __check_argument_count(self) -> bool:
        if not await self._validate_argument_count(
            self._message, 2, await self.get_response(RK.NO_USER_ID_PROVIDED),
        ):
            await self.reply_error(RK.NO_USER_ID_PROVIDED)
            return False
        return True

    async def __validate_user_id_and_days(self) -> bool:
        content = self._message.get_text().split()
        if not content[1].isdigit() or not content[2].isdigit():
            await self.reply_error(RK.NO_USER_ID_PROVIDED)
            return False
        return True

    async def _do_handle(self) -> None:
        content = self._message.get_text().split()
        user_id = int(content[1])
        days = int(content[2])

        new_end_date = await DatabaseManager.add_subscription(user_id, days)
        if new_end_date is None:
            await self.__reply_subscription_error()
            return

        await self.__reply_subscription_extended(user_id, new_end_date)

    async def __reply_subscription_extended(self, user_id: int, new_end_date: date) -> None:
        await self.reply(
            RK.SUBSCRIPTION_EXTENDED,
            args=[str(user_id), str(new_end_date)],
            data={"user_id": user_id, "new_end_date": str(new_end_date)},
        )
        await self._log_system_message(
            logging.INFO,
            get_subscription_log_message(str(user_id), self._message.get_username()),
        )

    async def __reply_subscription_error(self) -> None:
        await self.reply_error(RK.SUBSCRIPTION_ERROR)
        await self._log_system_message(logging.ERROR, get_subscription_error_log_message())
