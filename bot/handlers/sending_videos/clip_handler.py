import json
import logging
import math
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.models import ClipType
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import get_log_no_segments_found_message
from bot.responses.sending_videos.clip_handler_responses import (
    get_clip_trimmed_message,
    get_log_clip_success_message,
    get_log_clip_trimmed_message,
    get_log_segment_saved_message,
    get_message_too_long_message,
    get_no_quote_provided_message,
    get_no_segments_found_message,
)
from bot.search.text_segments_finder import TextSegmentsFinder
from bot.services.scene_snap.scene_snap_service import SceneSnapService
from bot.settings import settings
from bot.utils.constants import SegmentKeys
from bot.video.clips_extractor import ClipsExtractor


class ClipHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["klip", "clip", "k"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__validate_count,
            self.__validate_length,
        ]

    def _get_usage_message(self) -> str:
        return get_no_quote_provided_message()

    async def __validate_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, math.inf)

    async def __validate_length(self) -> bool:
        msg = self._message
        if not await DatabaseManager.is_admin_or_moderator(msg.get_user_id()) \
                and len(msg.get_text()) > settings.MAX_SEARCH_QUERY_LENGTH:
            await self._reply_error(get_message_too_long_message())
            return False
        return True

    async def _do_handle(self) -> None:
        msg = self._message
        content = msg.get_text().split()
        quote = " ".join(content[1:])

        active_series = await self._get_user_active_series(msg.get_user_id())

        results = await TextSegmentsFinder.find_segment_by_quote(
            quote, self._logger, active_series, size=settings.MAX_ES_RESULTS_QUICK,
        )
        if not results:
            return await self.__reply_no_segments_found(quote)

        segments = results if isinstance(results, list) else [results]

        await DatabaseManager.insert_last_search(
            chat_id=msg.get_chat_id(),
            quote=quote,
            segments=json.dumps(segments),
        )

        segment = segments[0]
        start_time = max(0, segment[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE)
        end_time = segment[SegmentKeys.END_TIME] + settings.EXTEND_AFTER

        start_time, end_time = await SceneSnapService.snap_clip_times(
            active_series, segment, start_time, end_time, self._logger,
        )

        segment_id = segment.get(SegmentKeys.SEGMENT_ID, segment.get(SegmentKeys.ID))
        is_admin = await DatabaseManager.is_admin_or_moderator(msg.get_user_id())
        max_duration = settings.MAX_CLIP_DURATION_HARD_LIMIT if is_admin else settings.MAX_CLIP_DURATION
        clip_duration = end_time - start_time
        if clip_duration > max_duration:
            await self._responder.send_markdown(get_clip_trimmed_message(max_duration))
            await self._log_system_message(logging.INFO, get_log_clip_trimmed_message(segment_id, clip_duration, max_duration))
            end_time = start_time + max_duration
            clip_duration = max_duration

        output_filename = await ClipsExtractor.extract_clip(segment[SegmentKeys.VIDEO_PATH], start_time, end_time, self._logger)

        await self._responder.send_video(
            output_filename,
            duration=clip_duration,
            suggestions=["Uzyj /w N aby wybrac inny wynik"],
        )

        await DatabaseManager.insert_last_clip(
            chat_id=msg.get_chat_id(),
            segment=segment,
            compiled_clip=None,
            clip_type=ClipType.SINGLE,
            adjusted_start_time=start_time,
            adjusted_end_time=end_time,
            is_adjusted=False,
        )

        return await self.__log_segment_and_clip_success(msg.get_chat_id(), msg.get_username())

    async def __reply_no_segments_found(self, quote: str) -> None:
        await self._reply_error(get_no_segments_found_message())
        await self._log_system_message(logging.INFO, get_log_no_segments_found_message(quote))

    async def __log_segment_and_clip_success(self, chat_id: int, username: str) -> None:
        await self._log_system_message(logging.INFO, get_log_segment_saved_message(chat_id))
        await self._log_system_message(logging.INFO, get_log_clip_success_message(username))
