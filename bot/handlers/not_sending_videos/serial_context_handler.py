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
        self._serial_manager = SerialContextManager(logger)

    def get_commands(self) -> List[str]:
        return ["serial", "series" ,"ser"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            lambda: self._validate_argument_count(
                self._message,
                min_args=0,
                max_args=1,
                error_message=get_serial_usage_message(),
            ),
        ]

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        user_id = self._message.get_user_id()
        available_series = await self._serial_manager.list_available_series()

        if len(args) == 1:
            current_series = await self._serial_manager.get_user_active_series(user_id)
            await self.reply(get_serial_current_message(current_series, available_series))
            return

        series_name = args[1].lower()
        available_series_lower = [s.lower() for s in available_series]

        if series_name not in available_series_lower:
            await self.reply_error(
                get_serial_invalid_message(series_name, available_series),
            )
            return

        await self._serial_manager.set_user_active_series(user_id, series_name)

        await self.reply(get_serial_changed_message(series_name))
        await self._log_system_message(
            logging.INFO,
            f"User {user_id} changed series to: {series_name}",
        )
