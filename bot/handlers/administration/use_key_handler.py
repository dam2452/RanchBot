import logging
from typing import List

from bot.database import db
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.use_key_handler_responses import (
    get_invalid_key_message,
    get_log_message_saved,
    get_no_message_provided_message,
    get_subscription_redeemed_message,
)


class SaveUserKeyHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["klucz", "key"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_no_message_provided_message())

    async def _do_handle(self) -> None:
        key = self._message.get_text().split(maxsplit=1)[1]
        user_id = self._message.get_user_id()
        username = self._message.get_username()
        full_name = self._message.get_full_name()

        subscription_days = await db.get_subscription_days_by_key(key)
        if subscription_days:
            await db.add_user(user_id, username, full_name, None)
            await db.add_subscription(user_id, subscription_days)
            await db.remove_subscription_key(key)

            await self._reply(get_subscription_redeemed_message(subscription_days), data={"days": subscription_days})
        else:
            await self._reply_error(get_invalid_key_message())

        await self._log_system_message(
            logging.INFO,
            get_log_message_saved(user_id),
        )
