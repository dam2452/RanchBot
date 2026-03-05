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
from bot.responses.not_sending_videos.semantic_search_handler_responses import get_embeddings_not_indexed_message
from bot.responses.sending_videos.semantic_clip_handler_responses import (
    get_log_semantic_clip_message,
    get_no_query_provided_message,
    get_no_results_found_message,
)


class SemanticClipHandler(SemanticHandlerMixin, BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["klipsens", "ksen", "ks"]

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
            await self._reply_error(get_embeddings_not_indexed_message(active_series, mode))
            return

        unique = self._deduplicate_semantic_results(results, mode)

        if not unique:
            await self._reply_error(get_no_results_found_message(query))
            return

        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=query,
            segments=json.dumps(unique),
        )

        if await self._send_top_segment_as_clip(unique[0], active_series):
            return

        await self._log_system_message(
            logging.INFO,
            get_log_semantic_clip_message(query, self._message.get_username(), mode),
        )
