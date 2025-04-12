from datetime import date
import logging
from typing import (
    List,
    Optional,
    Tuple,
)

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.subscription_status_handler_responses import (
    get_log_no_active_subscription_message,
    get_log_subscription_status_sent_message,
)


class SubscriptionStatusHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["subskrypcja", "subscription", "sub"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    async def _do_handle(self) -> None:
        user_id = self._message.get_user_id()
        username = self._message.get_username()

        subscription_status = await self.__get_subscription_status(user_id)
        if subscription_status is None:
            return await self.__reply_no_subscription(username)

        subscription_end, days_remaining = subscription_status

        if self._message.should_reply_json():
            await self.reply(
                key="",
                data={
                    "username": username,
                    "subscription_end": subscription_end.isoformat(),
                    "days_remaining": days_remaining,
                },
            )
        else:
            await self.reply(
                RK.SUBSCRIPTION_STATUS,
                args=[username, str(subscription_end), str(days_remaining)],
            )

        await self._log_system_message(
            logging.INFO,
            get_log_subscription_status_sent_message(username),
        )

    @staticmethod
    async def __get_subscription_status(user_id: int) -> Optional[Tuple[date, int]]:
        subscription_end = await DatabaseManager.get_user_subscription(user_id)
        if subscription_end is None:
            return None
        days_remaining = (subscription_end - date.today()).days
        return subscription_end, days_remaining

    async def __reply_no_subscription(self, username: str) -> None:
        await self.reply_error(RK.NO_SUBSCRIPTION)
        await self._log_system_message(
            logging.INFO,
            get_log_no_active_subscription_message(username),
        )
