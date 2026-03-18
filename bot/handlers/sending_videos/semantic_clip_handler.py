import json
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from bot.database.database_manager import DatabaseManager
from bot.handlers.semantic_bot_handler import SemanticBotHandler
from bot.responses.not_sending_videos.filter_handler_responses import get_filter_expired_message
from bot.responses.not_sending_videos.semantic_search_handler_responses import get_embeddings_not_indexed_message
from bot.responses.sending_videos.semantic_clip_handler_responses import (
    get_log_semantic_clip_message,
    get_no_query_provided_message,
    get_no_results_found_message,
)
from bot.search.filter_applicator import FilterApplicator
from bot.search.semantic_segments_finder import SemanticSearchMode
from bot.services.search_filter import SearchFilterService
from bot.settings import settings


class SemanticClipHandler(SemanticBotHandler):
    def get_commands(self) -> List[str]:
        return ["klipsens", "ksen", "ks"]

    def _get_usage_message(self) -> str:
        return get_no_query_provided_message()

    def _parse_semantic_mode_and_query(self) -> Tuple[SemanticSearchMode, str]:
        tokens = self._message.get_text().split()[1:]
        return SemanticSearchMode.FRAMES, " ".join(tokens)

    async def _handle_semantic_results(
        self,
        mode: SemanticSearchMode,
        query: str,
        active_series: str,
        results: Optional[List[Dict[str, Any]]],
    ) -> None:
        if results is None:
            await self._reply_error(get_embeddings_not_indexed_message(active_series, mode))
            return

        chat_id = self._message.get_chat_id()
        search_filter, expired = await SearchFilterService.get_active_filters_with_expiry(chat_id)
        if expired:
            await self._reply(get_filter_expired_message())

        if search_filter:
            results = await FilterApplicator.apply_to_text_segments(
                results, search_filter, active_series, self._logger,
            )

        unique = self._deduplicate_semantic_results(results, mode)[:settings.MAX_ES_RESULTS_QUICK]

        if not unique:
            await self._reply_error(get_no_results_found_message(query))
            return

        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=query,
            segments=json.dumps(unique),
        )

        if await self._send_top_segment_as_clip(unique[0], active_series):
            await self._log_system_message(
                logging.INFO,
                get_log_semantic_clip_message(query, self._message.get_username(), mode),
            )
