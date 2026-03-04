import json
import logging
import math
from typing import (
    Any,
    Dict,
    List,
)

from bot.database.database_manager import DatabaseManager
from bot.database.models import ClipType
from bot.exceptions.vllm_exceptions import (
    VllmConnectionError,
    VllmTimeoutError,
)
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import get_message_too_long_message
from bot.responses.not_sending_videos.semantic_search_handler_responses import (
    get_embeddings_not_indexed_message,
    get_vllm_unavailable_message,
)
from bot.responses.sending_videos.semantic_clip_handler_responses import (
    get_log_semantic_clip_message,
    get_no_query_provided_message,
    get_no_results_found_message,
    get_no_video_path_message,
)
from bot.search.semantic_segments_finder import (
    SemanticSearchMode,
    SemanticSegmentsFinder,
)
from bot.services.scene_snap.scene_snap_service import SceneSnapService
from bot.settings import settings
from bot.utils.constants import SegmentKeys
from bot.video.clips_extractor import ClipsExtractor


class SemanticClipHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["sens_klip", "senk", "sk"]

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
            await self._reply_error(get_embeddings_not_indexed_message(active_series, mode))
            return

        unique = self.__deduplicate(results, mode)

        if not unique:
            await self._reply_error(get_no_results_found_message(query))
            return

        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=query,
            segments=json.dumps(unique),
        )

        top_segment = unique[0]
        if not top_segment.get(SegmentKeys.VIDEO_PATH):
            await self._reply_error(get_no_video_path_message())
            return

        start_time = max(0, top_segment[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE)
        end_time = top_segment[SegmentKeys.END_TIME] + settings.EXTEND_AFTER

        start_time, end_time = await SceneSnapService.snap_clip_times(
            active_series, top_segment, start_time, end_time, self._logger,
        )

        clip_duration = end_time - start_time
        if await self._handle_clip_duration_limit_exceeded(clip_duration):
            return

        output_filename = await ClipsExtractor.extract_clip(
            top_segment[SegmentKeys.VIDEO_PATH], start_time, end_time, self._logger,
        )

        await self._responder.send_video(
            output_filename,
            duration=clip_duration,
            suggestions=["Uzyj /w N aby wybrac inny wynik"],
        )

        await DatabaseManager.insert_last_clip(
            chat_id=self._message.get_chat_id(),
            segment=top_segment,
            compiled_clip=None,
            clip_type=ClipType.SINGLE,
            adjusted_start_time=start_time,
            adjusted_end_time=end_time,
            is_adjusted=False,
        )

        await self._log_system_message(
            logging.INFO,
            get_log_semantic_clip_message(query, self._message.get_username(), mode),
        )

    @staticmethod
    def __deduplicate(results: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
        if mode == SemanticSearchMode.FRAMES:
            return SemanticSegmentsFinder.deduplicate_frames(results)
        if mode == SemanticSearchMode.EPISODE:
            return SemanticSegmentsFinder.deduplicate_episodes(results)
        return SemanticSegmentsFinder.deduplicate_segments(results)
