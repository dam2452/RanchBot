import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.link_account_handler_responses import (
    get_already_linked_message,
    get_invalid_args_message,
    get_invalid_code_message,
    get_link_success_message,
)


class LinkAccountHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["link"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_invalid_args_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1)

    async def _do_handle(self) -> None:
        telegram_user_id = self._message.get_user_id()

        if await DatabaseManager.has_credentials(telegram_user_id):
            await self._reply(get_already_linked_message())
            return

        args = self._message.get_text().split()
        code = args[1].strip()

        rest_user_id = await DatabaseManager.consume_verification_token(
            token=code,
            purpose="telegram_link",
        )

        if rest_user_id is None:
            await self._reply_error(get_invalid_code_message())
            await self._log_system_message(logging.INFO, f"Invalid link code from Telegram user {telegram_user_id}")
            return

        rest_profile = await DatabaseManager.get_user_by_id(rest_user_id)
        if not rest_profile:
            await self._reply_error(get_invalid_code_message())
            return

        await DatabaseManager.link_telegram_account(
            rest_user_id=rest_user_id,
            telegram_user_id=telegram_user_id,
            telegram_username=self._message.get_username(),
            telegram_full_name=self._message.get_full_name(),
        )

        await self._reply(
            get_link_success_message(rest_profile.username or ""),
            data={"rest_username": rest_profile.username},
        )
        await self._log_system_message(
            logging.INFO,
            f"Telegram user {telegram_user_id} linked to REST account {rest_profile.username}",
        )
