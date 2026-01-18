import json
import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.models import (
    ClipType,
    SearchHistory,
)
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.sending_videos.adjust_video_clip_handler_responses import (
    get_extraction_failure_log,
    get_invalid_interval_log,
    get_invalid_segment_log,
    get_no_previous_searches_log,
    get_no_quotes_selected_log,
    get_successful_adjustment_message,
    get_updated_segment_info_log,
)
from bot.settings import settings
from bot.video.clips_extractor import ClipsExtractor
from bot.video.utils import (
    FFMpegException,
    get_video_duration,
)


class AdjustVideoClipHandler(BotMessageHandler):
    __RELATIVE_COMMANDS: List[str] = ["dostosuj", "adjust", "d"]
    __ABSOLUTE_COMMANDS: List[str] = ["adostosuj", "aadjust", "ad"]


    def get_commands(self) -> List[str]:
        return AdjustVideoClipHandler.__RELATIVE_COMMANDS + AdjustVideoClipHandler.__ABSOLUTE_COMMANDS

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 2, await self.get_response(RK.INVALID_ARGS_COUNT), 3)

    async def _do_handle(self) -> None:
        msg = self._message
        content = msg.get_text().split()
        segment_info = {}
        last_clip = None

        if len(content) == 4:
            last_search: SearchHistory = await DatabaseManager.get_last_search_by_chat_id(msg.get_chat_id())
            if not last_search:
                return await self.__reply_no_previous_searches()
            try:
                index = int(content[1]) - 1
                segments = json.loads(last_search.segments)
                segment_info = segments[index]
            except (ValueError, IndexError):
                return await self.__reply_invalid_segment_index()
        elif len(content) == 3:
            last_clip = await DatabaseManager.get_last_clip_by_chat_id(msg.get_chat_id())
            if not last_clip:
                return await self.__reply_no_quotes_selected()

            segment_info = last_clip.segment
            if isinstance(segment_info, str):
                segment_info = json.loads(segment_info)

            await self._log_system_message(logging.INFO, f"Segment Info: {segment_info}")

        original_start_time = float(segment_info.get("start", 0))
        original_end_time = float(segment_info.get("end", 0))

        try:
            float(content[-2])
            float(content[-1])
        except ValueError:
            return await self._reply_invalid_args_count(await self.get_response(RK.INVALID_ARGS_COUNT))

        additional_start_offset = float(content[-2])
        additional_end_offset = float(content[-1])

        is_consecutive_adjustment = content[0].lstrip('/') in AdjustVideoClipHandler.__RELATIVE_COMMANDS and last_clip and last_clip.is_adjusted

        if is_consecutive_adjustment:
            original_start_time = last_clip.adjusted_start_time or original_start_time
            original_end_time = last_clip.adjusted_end_time or original_end_time
            await self._log_system_message(logging.INFO, f"Relative adjustment. Last clip: {last_clip}")

        if await self.__is_adjustment_exceeding_limits(additional_start_offset, additional_end_offset):
            return await self._answer(await self.get_response(RK.MAX_EXTENSION_LIMIT))

        # prevent adding extra padding in sequential adjustments while keeping the minimum clip length for the first use
        extend_before = 0 if is_consecutive_adjustment else settings.EXTEND_BEFORE
        extend_after = 0 if is_consecutive_adjustment else settings.EXTEND_AFTER

        start_time = max(0.0, original_start_time - additional_start_offset - extend_before)
        end_time = min(original_end_time + additional_end_offset + extend_after, await get_video_duration(segment_info.get("video_path")))

        if await self._handle_clip_duration_limit_exceeded(end_time - start_time):
            return None

        try:
            output_filename = await ClipsExtractor.extract_clip(segment_info.get("video_path"), start_time, end_time, self._logger)
            await self._responder.send_video(output_filename)

            await DatabaseManager.insert_last_clip(
                chat_id=msg.get_chat_id(),
                segment=segment_info,
                compiled_clip=None,
                clip_type=ClipType.ADJUSTED,
                adjusted_start_time=start_time,
                adjusted_end_time=end_time,
                is_adjusted=True,
            )
        except ValueError:
            return await self.__reply_invalid_interval()
        except FFMpegException as e:
            return await self.__reply_extraction_failure(e)

        await self._log_system_message(logging.INFO, get_updated_segment_info_log(msg.get_chat_id()))
        return await self._log_system_message(logging.INFO, get_successful_adjustment_message(msg.get_username()))

    async def __reply_no_previous_searches(self) -> None:
        await self._answer(await self.get_response(RK.NO_PREVIOUS_SEARCHES))
        await self._log_system_message(logging.INFO, get_no_previous_searches_log())

    async def __reply_no_quotes_selected(self) -> None:
        await self._answer(await self.get_response(RK.NO_QUOTES_SELECTED))
        await self._log_system_message(logging.INFO, get_no_quotes_selected_log())

    async def __reply_invalid_interval(self) -> None:
        await self._answer(await self.get_response(RK.INVALID_INTERVAL))
        await self._log_system_message(logging.INFO, get_invalid_interval_log())

    async def __reply_invalid_segment_index(self) -> None:
        await self._answer(await self.get_response(RK.INVALID_SEGMENT_INDEX))
        await self._log_system_message(logging.INFO, get_invalid_segment_log())

    async def __reply_extraction_failure(self, e: Exception) -> None:
        await self._answer(await self.get_response(RK.EXTRACTION_FAILURE, as_parent=True))
        await self._log_system_message(logging.ERROR, get_extraction_failure_log(e))

    async def __is_adjustment_exceeding_limits(self, additional_start_offset: float, additional_end_offset: float) -> bool:
        return (
            not await DatabaseManager.is_admin_or_moderator(self._message.get_user_id()) and
            abs(additional_start_offset) + abs(additional_end_offset) > settings.MAX_ADJUSTMENT_DURATION
        )
