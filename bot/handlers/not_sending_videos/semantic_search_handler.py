import json
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import BotMessageHandler
from bot.handlers.semantic_handler_mixin import SemanticHandlerMixin
from bot.responses.bot_message_handler_responses import (
    get_log_no_segments_found_message,
    get_no_segments_found_message,
)
from bot.responses.not_sending_videos.semantic_search_handler_responses import (
    format_semantic_episodes_response,
    format_semantic_frames_response,
    format_semantic_search_response,
    get_embeddings_not_indexed_message,
    get_log_semantic_search_results_sent_message,
    get_no_query_provided_message,
)
from bot.search.semantic_segments_finder import SemanticSearchMode


class SemanticSearchHandler(SemanticHandlerMixin, BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["sens", "meaning", "sen"]

    def _get_usage_message(self) -> str:
        return get_no_query_provided_message()

    async def _handle_semantic_results(
        self,
        mode: str,
        query: str,
        active_series: str,
        results: Optional[List[Dict[str, Any]]],
    ) -> None:
        if results is None:
            await self.__reply_embeddings_not_indexed(active_series, mode, query)
            return

        if not results:
            await self.__reply_no_segments_found(query)
            return

        unique = self._deduplicate_semantic_results(results, mode)

        if mode != SemanticSearchMode.EPISODE:
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
    def __format_response(unique: list, query: str, mode: str) -> str:
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
