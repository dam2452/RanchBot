import json
import logging
from pathlib import Path
import tempfile
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.search_list_handler_responses import (
    format_search_list_response,
    get_log_no_previous_search_results_message,
    get_log_search_results_sent_message,
    get_no_previous_search_results_message,
)
from bot.search.transcription_finder import TranscriptionFinder
from bot.settings import settings as s


class SearchListHandler(BotMessageHandler):
    FILE_NAME_TEMPLATE = s.BOT_USERNAME + "_Lista_{sanitized_search_term}.txt"

    def get_commands(self) -> List[str]:
        return ["lista", "list", "l"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_last_search_exists]

    async def __check_last_search_exists(self) -> bool:
        user_id = self._message.get_user_id()
        series_id = await self._get_user_active_series_id(user_id)
        last_search = await DatabaseManager.get_last_search_by_chat_id(self._message.get_chat_id(), series_id)
        if not last_search:
            await self.__reply_no_previous_search_results()
            return False
        return True

    async def _do_handle(self) -> None:
        user_id = self._message.get_user_id()
        series_id = await self._get_user_active_series_id(user_id)
        last_search = await DatabaseManager.get_last_search_by_chat_id(self._message.get_chat_id(), series_id)

        try:
            segments = json.loads(last_search.segments)
        except (json.JSONDecodeError, TypeError):
            return await self.__reply_no_previous_search_results()

        search_term = last_search.quote
        if not segments or not search_term:
            return await self.__reply_no_previous_search_results()

        if self._message.should_reply_json():
            series_name = await self._get_user_active_series(user_id)
            season_info = await TranscriptionFinder.get_season_details_from_elastic(logger=self._logger, series_name=series_name)
            await self._responder.send_json({
                "query": search_term,
                "segments": segments,
                "season_info": season_info,
            })
        else:
            response = format_search_list_response(search_term, segments)
            sanitized_search_term = self.__sanitize_search_term(search_term)
            file_path = Path(tempfile.gettempdir()) / self.FILE_NAME_TEMPLATE.format(
                sanitized_search_term=sanitized_search_term,
            )

            with file_path.open("w", encoding="utf-8") as file:
                file.write(response)

            await self._responder.send_document(file_path, caption="📄 Wszystkie znalezione cytaty 📄")

        return await self._log_system_message(
            logging.INFO,
            get_log_search_results_sent_message(search_term, self._message.get_username()),
        )

    async def __reply_no_previous_search_results(self) -> None:
        await self.reply_error(get_no_previous_search_results_message())
        await self._log_system_message(
            logging.INFO,
            get_log_no_previous_search_results_message(self._message.get_chat_id()),
        )

    @staticmethod
    def __sanitize_search_term(search_term: str) -> str:
        allowed_characters = [c.isalpha() or c.isdigit() or c == " " for c in search_term]
        filtered_chars = [c for c, allowed in zip(search_term, allowed_characters) if allowed]
        filtered_string = "".join(filtered_chars)
        return filtered_string.rstrip().replace(" ", "_")
