import logging
import math
from typing import List

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.serial_context_handler_responses import (
    get_no_series_name_provided_message,
    get_serial_changed_message,
    get_serial_current_message,
    get_serial_invalid_message,
)
from bot.utils.functions import find_matching_series


class SerialContextHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["serial", "series", "ser"]

    def _get_usage_message(self) -> str:
        return get_no_series_name_provided_message()

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            lambda: self._validate_argument_count(
                self._message,
                min_args=0,
                max_args=math.inf,
            ),
        ]

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        user_id = self._message.get_user_id()
        available_series = await self._serial_manager.list_available_series()

        if len(args) == 1:
            current_series = await self._serial_manager.get_user_active_series(user_id)
            await self._reply(get_serial_current_message(current_series, available_series))
            return

        query = " ".join(args[1:])
        matched = find_matching_series(query, available_series)

        if matched is None:
            await self._reply_error(
                get_serial_invalid_message(query, available_series),
            )
            return

        await self._serial_manager.set_user_active_series(user_id, matched)

        await self._reply(get_serial_changed_message(matched))
        await self._log_system_message(
            logging.INFO,
            f"User {user_id} changed series to: {matched}",
        )
