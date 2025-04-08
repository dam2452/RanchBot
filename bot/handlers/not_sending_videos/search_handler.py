import json
import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import get_log_no_segments_found_message
from bot.responses.not_sending_videos.search_handler_responses import (
    format_search_response,
    get_log_search_results_sent_message,
)
from bot.search.transcription_finder import TranscriptionFinder
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
        return await self._validate_argument_count(
            self._message, 2, await self.get_response(RK.INVALID_ARGS_COUNT),
        )

    async def __check_quote_length(self) -> bool:
        args = self._message.get_text().split()
        quote = " ".join(args[1:])
        if not await DatabaseManager.is_admin_or_moderator(self._message.get_user_id()) and len(quote) > settings.MAX_SEARCH_QUERY_LENGTH:
            await self.reply_error(RK.MESSAGE_TOO_LONG)
            return False
        return True

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        quote = " ".join(args[1:])

        segments = await TranscriptionFinder.find_segment_by_quote(quote, self._logger, return_all=True)
        if not segments:
            await self.__reply_no_segments_found(quote)
            return

        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=quote,
            segments=json.dumps(segments),
        )

        if self._message.get_json_flag():
            await self.reply(
                key="",
                data={
                    "quote": quote,
                    "results": segments,
                },
            )
        else:
            season_info = await TranscriptionFinder.get_season_details_from_elastic(logger=self._logger)
            response = format_search_response(len(segments), segments, quote, season_info)
            await self.__send_search_results(response, quote)

    async def __reply_no_segments_found(self, quote: str) -> None:
        await self.reply_error(RK.NO_SEGMENTS_FOUND, args=[quote], as_parent=True)
        await self._log_system_message(logging.INFO, get_log_no_segments_found_message(quote))

    async def __send_search_results(self, response: str, quote: str) -> None:
        await self._responder.send_markdown(response)
        await self._log_system_message(logging.INFO, get_log_search_results_sent_message(quote, self._message.get_username()))
