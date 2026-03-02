import json
import logging
import math
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.exceptions.vllm_exceptions import (
    VllmConnectionError,
    VllmTimeoutError,
)
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import (
    get_log_no_segments_found_message,
    get_message_too_long_message,
    get_no_segments_found_message,
)
from bot.responses.not_sending_videos.semantic_search_handler_responses import (
    format_semantic_episodes_response,
    format_semantic_frames_response,
    format_semantic_search_response,
    get_embeddings_not_indexed_message,
    get_log_semantic_search_results_sent_message,
    get_no_query_provided_message,
    get_vllm_unavailable_message,
)
from bot.search.semantic_segments_finder import (
    SemanticSearchMode,
    SemanticSegmentsFinder,
)
from bot.settings import settings


class SemanticSearchHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["sens", "meaning", "sen"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_query_length,
        ]

    def _get_usage_message(self) -> str:
        return get_no_query_provided_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, math.inf)

    async def __check_query_length(self) -> bool:
        _, query = self.__parse_mode_and_query()
        if not await DatabaseManager.is_admin_or_moderator(self._message.get_user_id()) and len(
                query,
        ) > settings.MAX_SEARCH_QUERY_LENGTH:
            await self._reply_error(get_message_too_long_message())
            return False
        return True

    def __parse_mode_and_query(self) -> tuple:
        args = self._message.get_text().split()
        tokens = args[1:]
        if tokens:
            mode = SemanticSearchMode.from_str(tokens[0])
            if mode is not None:
                return mode, " ".join(tokens[1:])
        return SemanticSearchMode.DEFAULT, " ".join(tokens)

    async def _do_handle(self) -> None:
        mode, query = self.__parse_mode_and_query()

        if not query:
            await self._reply_error(get_no_query_provided_message())
            return

        user_id = self._message.get_user_id()
        active_series = await self._get_user_active_series(user_id)

        try:
            results = await SemanticSegmentsFinder.find_by_text(
                query, self._logger, active_series, mode=mode, size=999,
            )
        except VllmConnectionError:
            await self._reply_error(get_vllm_unavailable_message())
            return
        except VllmTimeoutError:
            await self._reply_error(get_vllm_unavailable_message())
            return

        if results is None:
            await self.__reply_embeddings_not_indexed(active_series, mode, query)
            return

        if not results:
            await self.__reply_no_segments_found(query)
            return

        unique = self.__deduplicate(results, mode)

        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=query,
            segments=json.dumps(unique),
        )

        response = self.__format_response(unique, query, mode)

        await self._reply(response, data={"quote": query, "results": unique})
        await self._log_system_message(
            logging.INFO,
            get_log_semantic_search_results_sent_message(
                query, self._message.get_username(), mode,
            ),
        )

    @staticmethod
    def __deduplicate(results, mode: str):
        if mode == SemanticSearchMode.FRAMES:
            return SemanticSegmentsFinder.deduplicate_frames(results)
        if mode == SemanticSearchMode.EPISODE:
            return SemanticSegmentsFinder.deduplicate_episodes(results)
        return SemanticSegmentsFinder.deduplicate_segments(results)

    @staticmethod
    def __format_response(unique, query: str, mode: str) -> str:
        if mode == SemanticSearchMode.FRAMES:
            return format_semantic_frames_response(len(unique), unique, query)
        if mode == SemanticSearchMode.EPISODE:
            return format_semantic_episodes_response(len(unique), unique, query)
        return format_semantic_search_response(len(unique), unique, query)

    async def __reply_no_segments_found(self, query: str) -> None:
        await self._reply_error(get_no_segments_found_message(query))
        await self._log_system_message(logging.INFO, get_log_no_segments_found_message(query))

    async def __reply_embeddings_not_indexed(
        self, series_name: str, mode: str, query: str,
    ) -> None:
        await self._reply_error(get_embeddings_not_indexed_message(series_name, mode))
        await self._log_system_message(logging.INFO, get_log_no_segments_found_message(query))
