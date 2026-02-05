import json
import logging
import math
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import (
    get_log_no_segments_found_message,
    get_message_too_long_message,
    get_no_segments_found_message,
)
from bot.responses.not_sending_videos.search_handler_responses import (
    format_search_response,
    get_invalid_args_count_message,
    get_log_search_results_sent_message,
)
from bot.search.transcription_finder import TranscriptionFinder
from bot.services.serial_context.serial_context_manager import SerialContextManager
from bot.settings import settings


class SearchHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["szukaj", "search", "sz"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_quote_length,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_invalid_args_count_message(), math.inf)

    async def __check_quote_length(self) -> bool:
        args = self._message.get_text().split()
        quote = " ".join(args[1:])
        if not await DatabaseManager.is_admin_or_moderator(self._message.get_user_id()) and len(
                quote,
        ) > settings.MAX_SEARCH_QUERY_LENGTH:
            await self.reply_error(get_message_too_long_message())
            return False
        return True

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        quote = " ".join(args[1:])

        serial_manager = SerialContextManager(self._logger)
        active_series = await serial_manager.get_user_active_series(self._message.get_user_id())

        segments = await TranscriptionFinder.find_segment_by_quote(quote, self._logger, active_series, size=10000)
        if not segments:
            await self.__reply_no_segments_found(quote)
            return

        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=quote,
            segments=json.dumps(segments),
            series_name=active_series,
        )

        index = f"{active_series}_text_segments"
        season_info = await TranscriptionFinder.get_season_details_from_elastic(logger=self._logger, index=index)
        response = format_search_response(len(segments), segments, quote)

        await self.reply(
            response,
            data={
                "quote": quote,
                "results": segments,
            },
        )
        await self._log_system_message(logging.INFO, get_log_search_results_sent_message(quote, self._message.get_username()))

    async def __reply_no_segments_found(self, quote: str) -> None:
        await self.reply_error(get_no_segments_found_message(quote))
        await self._log_system_message(logging.INFO, get_log_no_segments_found_message(quote))
