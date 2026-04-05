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
from bot.search.filter_applicator import FilterApplicator
from bot.search.semantic_segments_finder import (
    SemanticSearchMode,
    SemanticSegmentsFinder,
)
from bot.settings import settings
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
)


class SemanticSearchHandler(SemanticBotHandler):
    __TEXT_COMMANDS: List[str] = ["sens", "meaning", "sen"]
    __FRAMES_COMMANDS: List[str] = ["sensklatki", "sensk"]
    __EPISODE_COMMANDS: List[str] = ["sensodcinek", "senso"]

    def get_commands(self) -> List[str]:
        return (
            SemanticSearchHandler.__TEXT_COMMANDS
            + SemanticSearchHandler.__FRAMES_COMMANDS
            + SemanticSearchHandler.__EPISODE_COMMANDS
        )

    def _parse_semantic_mode_and_query(self) -> Tuple[SemanticSearchMode, str]:
        command = self._message.get_text().split()[0].lstrip("/").lower()
        tokens = self._message.get_text().split()[1:]
        if command in SemanticSearchHandler.__FRAMES_COMMANDS:
            return SemanticSearchMode.FRAMES, " ".join(tokens)
        if command in SemanticSearchHandler.__EPISODE_COMMANDS:
            return SemanticSearchMode.EPISODE, " ".join(tokens)
        return super()._parse_semantic_mode_and_query()

    def _get_usage_message(self) -> str:
        return get_no_query_provided_message()

    async def _handle_semantic_results(
        self,
        mode: SemanticSearchMode,
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

        chat_id = self._message.get_chat_id()
        search_filter = await DatabaseManager.get_and_touch_user_filters(chat_id)

        if search_filter:
            if mode == SemanticSearchMode.EPISODE:
                seasons = FilterApplicator.get_seasons_list(search_filter)
                if seasons:
                    results = [
                        r for r in results
                        if r.get(EpisodeMetadataKeys.EPISODE_METADATA, {}).get(EpisodeMetadataKeys.SEASON) in seasons
                    ]
            else:
                results = await FilterApplicator.apply_to_text_segments(
                    results, search_filter, active_series, self._logger,
                )

        if not results:
            await self.__reply_no_segments_found(query)
            return

        unique = self._deduplicate_semantic_results(results, mode)

        if mode == SemanticSearchMode.EPISODE:
            unique = await self.__enrich_episode_results_with_clip_times(unique, active_series)

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

    async def __enrich_episode_results_with_clip_times(
        self, episodes: list, active_series: str,
    ) -> list:
        episode_ids = [ep.get("episode_id") for ep in episodes if ep.get("episode_id")]
        first_times = await SemanticSegmentsFinder.fetch_first_dialogue_times(
            episode_ids, active_series, self._logger,
        )
        for ep in episodes:
            episode_id = ep.get("episode_id", "")
            first_time = first_times.get(episode_id, 0.0)
            ep[SegmentKeys.START_TIME] = first_time
            ep[SegmentKeys.END_TIME] = first_time + settings.SENSODCINEK_PREVIEW_DURATION_SEC
        return episodes

    @staticmethod
    def __format_response(unique: list, query: str, mode: SemanticSearchMode) -> str:
        if mode == SemanticSearchMode.FRAMES:
            return format_semantic_frames_response(len(unique), unique, query)
        if mode == SemanticSearchMode.EPISODE:
            return format_semantic_episodes_response(len(unique), unique, query)
        return format_semantic_search_response(len(unique), unique, query)

    async def __reply_no_segments_found(self, query: str) -> None:
        await self._reply_error(get_no_segments_found_message(query))
        await self._log_system_message(logging.INFO, get_log_no_segments_found_message(query))

    async def __reply_embeddings_not_indexed(
        self, series_name: str, mode: SemanticSearchMode, query: str,
    ) -> None:
        await self._reply_error(get_embeddings_not_indexed_message(series_name, mode))
        await self._log_system_message(logging.INFO, get_log_no_segments_found_message(query))
