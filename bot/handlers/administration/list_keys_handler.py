import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.models import SubscriptionKey
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.list_keys_handler_responses import (
    create_subscription_keys_response,
    get_log_subscription_keys_empty_message,
    get_log_subscription_keys_sent_message,
    get_subscription_keys_empty_message,
)


class ListKeysHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["listkey", "lk"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    async def _do_handle(self) -> None:
        keys = await DatabaseManager.get_all_subscription_keys()
        if not keys:
            return await self.__reply_subscription_keys_empty()

        response = create_subscription_keys_response(keys)
        return await self.__reply_subscription_keys(response, keys)

    async def __reply_subscription_keys_empty(self) -> None:
        if self._message.should_reply_json():
            await self.reply("", data={"keys": []})
        else:
            await self._responder.send_text(get_subscription_keys_empty_message())

        await self._log_system_message(logging.INFO, get_log_subscription_keys_empty_message())

    async def __reply_subscription_keys(self, response: str, keys: List[SubscriptionKey]) -> None:
        if self._message.should_reply_json():
            await self.reply("", data={"keys": [k.to_dict() for k in keys]})
        else:
            await self._responder.send_markdown(response)

        await self._log_system_message(logging.INFO, get_log_subscription_keys_sent_message())
