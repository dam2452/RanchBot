from abc import abstractmethod
import math
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from bot.database.database_manager import DatabaseManager
from bot.exceptions.vllm_exceptions import (
    VllmConnectionError,
    VllmTimeoutError,
)
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import get_message_too_long_message
from bot.responses.not_sending_videos.semantic_search_handler_responses import get_vllm_unavailable_message
from bot.search.semantic_segments_finder import (
    SemanticSearchMode,
    SemanticSegmentsFinder,
)
from bot.settings import settings


class SemanticBotHandler(BotMessageHandler):
    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_semantic_argument_count,
            self.__check_semantic_query_length,
        ]

    async def __check_semantic_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, math.inf)

    async def __check_semantic_query_length(self) -> bool:
        _, query = self._parse_semantic_mode_and_query()
        if not await DatabaseManager.is_admin_or_moderator(
            self._message.get_user_id(),
        ) and len(query) > settings.MAX_SEARCH_QUERY_LENGTH:
            await self._reply_error(get_message_too_long_message())
            return False
        return True

    def _parse_semantic_mode_and_query(self) -> Tuple[SemanticSearchMode, str]:
        args = self._message.get_text().split()
        tokens = args[1:]
        if tokens:
            mode = SemanticSearchMode.from_str(tokens[0])
            if mode is not None:
                return mode, " ".join(tokens[1:])
        return SemanticSearchMode.DEFAULT, " ".join(tokens)

    async def _fetch_semantic_results(
        self,
        query: str,
        mode: SemanticSearchMode,
    ) -> Optional[Tuple[str, Optional[List[Dict[str, Any]]]]]:
        user_id = self._message.get_user_id()
        active_series = await self._get_user_active_series(user_id)
        try:
            results = await SemanticSegmentsFinder.find_by_text(
                query, self._logger, active_series, mode=mode,
            )
            return active_series, results
        except (VllmConnectionError, VllmTimeoutError):
            await self._reply_error(get_vllm_unavailable_message())
            return None

    async def _do_handle(self) -> None:
        mode, query = self._parse_semantic_mode_and_query()
        if not query:
            await self._reply_error(self._get_usage_message())
            return
        fetch_result = await self._fetch_semantic_results(query, mode)
        if fetch_result is None:
            return
        active_series, results = fetch_result
        await self._handle_semantic_results(mode, query, active_series, results)

    @abstractmethod
    async def _handle_semantic_results(
        self,
        mode: SemanticSearchMode,
        query: str,
        active_series: str,
        results: Optional[List[Dict[str, Any]]],
    ) -> None: pass

    @staticmethod
    def _deduplicate_semantic_results(
        results: List[Dict[str, Any]],
        mode: SemanticSearchMode,
    ) -> List[Dict[str, Any]]:
        if mode == SemanticSearchMode.FRAMES:
            return SemanticSegmentsFinder.deduplicate_frames(results)
        if mode == SemanticSearchMode.EPISODE:
            return SemanticSegmentsFinder.deduplicate_episodes(results)
        return SemanticSegmentsFinder.deduplicate_segments(results)
