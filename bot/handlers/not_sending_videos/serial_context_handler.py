import logging
from typing import List

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.serial_context_handler_responses import (
    get_serial_changed_message,
    get_serial_current_message,
    get_serial_invalid_message,
    get_serial_usage_message,
)
from bot.services.serial_context.serial_context_manager import SerialContextManager


class SerialContextHandler(BotMessageHandler):
    def __init__(self, message, responder, logger):
        super().__init__(message, responder, logger)
        self.serial_manager = SerialContextManager(logger)

    def get_commands(self) -> List[str]:
        return ["serial", "series" ,"ser"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
        ]

    async def __check_argument_count(self) -> bool:
        args = self._message.get_text().split()

        if len(args) > 2:
            await self.reply_error(get_serial_usage_message())
            return False

        return True

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        user_id = self._message.get_user_id()

        if len(args) == 1:
            current_series = await self.serial_manager.get_user_active_series(
                user_id,
            )
            await self.reply(get_serial_current_message(current_series))
            return

        series_name = args[1].lower()

        available_series = await self.serial_manager.list_available_series()
        if series_name not in available_series:
            await self.reply_error(
                get_serial_invalid_message(series_name, available_series),
            )
            return

        await self.serial_manager.set_user_active_series(user_id, series_name)

        await self.reply(get_serial_changed_message(series_name))
        await self._log_system_message(
            logging.INFO,
            f"User {user_id} changed series to: {series_name}",
        )
