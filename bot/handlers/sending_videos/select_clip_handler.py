import json
import logging
from pathlib import Path
import tempfile
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.models import ClipType
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.sending_videos.select_clip_handler_responses import (
    get_invalid_args_count_message,
    get_invalid_segment_number_message,
    get_log_invalid_segment_number_message,
    get_log_no_previous_search_message,
    get_log_segment_selected_message,
    get_no_previous_search_message,
)
from bot.settings import settings
from bot.utils.constants import SegmentKeys
from bot.video.clips_extractor import ClipsExtractor


class SelectClipHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["wybierz", "select", "w"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_invalid_args_count_message())

    async def _do_handle(self) -> None:
        content = self._message.get_text().split()

        last_search = await DatabaseManager.get_last_search_by_chat_id(self._message.get_chat_id())
        if not last_search:
            return await self.__reply_no_previous_search()

        if not content[1].lstrip('-').isdigit():
            return await self.__reply_invalid_segment_number(-1)
        index = int(content[1])

        segments = json.loads(last_search.segments)
        if index not in range(1, len(segments) + 1):
            return await self.__reply_invalid_segment_number(index)

        segment = segments[index - 1]
        start_time = max(0, segment[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE)
        end_time = segment[SegmentKeys.END_TIME] + settings.EXTEND_AFTER

        if await self._handle_clip_duration_limit_exceeded(end_time - start_time):
            return None

        segment_id = segment.get(SegmentKeys.SEGMENT_ID, segment.get(SegmentKeys.ID))

        output_filename = await ClipsExtractor.extract_clip(segment[SegmentKeys.VIDEO_PATH], start_time, end_time, self._logger)
        temp_file_path = Path(tempfile.gettempdir()) / f"selected_clip_{segment_id}.mp4"
        output_filename.replace(temp_file_path)

        clip_duration = end_time - start_time
        if not await self._responder.send_video(
            temp_file_path,
            duration=clip_duration,
            suggestions=["Wybrać krótszy fragment"],
        ):
            await self._log_clip_too_large_failure(clip_duration)
            return None

        await DatabaseManager.insert_last_clip(
            chat_id=self._message.get_chat_id(),
            segment=segment,
            compiled_clip=None,
            clip_type=ClipType.SELECTED,
            adjusted_start_time=None,
            adjusted_end_time=None,
            is_adjusted=False,
        )

        return await self._log_system_message(
            logging.INFO,
            get_log_segment_selected_message(segment_id, self._message.get_username()),
        )

    async def __reply_no_previous_search(self) -> None:
        await self.reply_error(get_no_previous_search_message())
        await self._log_system_message(logging.INFO, get_log_no_previous_search_message())

    async def __reply_invalid_segment_number(self, segment_number: int) -> None:
        await self.reply_error(get_invalid_segment_number_message())
        await self._log_system_message(logging.WARNING, get_log_invalid_segment_number_message(segment_number))
