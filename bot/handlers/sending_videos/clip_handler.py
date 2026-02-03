import logging
import math
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.models import ClipType
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import (
    get_extraction_failure_message,
    get_log_extraction_failure_message,
    get_log_no_segments_found_message,
)
from bot.responses.sending_videos.clip_handler_responses import (
    get_log_clip_success_message,
    get_log_segment_saved_message,
    get_message_too_long_message,
    get_no_quote_provided_message,
    get_no_segments_found_message,
)
from bot.search.transcription_finder import TranscriptionFinder
from bot.services.serial_context.serial_context_manager import SerialContextManager
from bot.settings import settings
from bot.video.clips_extractor import ClipsExtractor
from bot.video.utils import FFMpegException


class ClipHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["klip", "clip", "k"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__validate_count,
            self.__validate_length,
        ]

    async def __validate_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_no_quote_provided_message(), math.inf)

    async def __validate_length(self) -> bool:
        msg = self._message
        if not await DatabaseManager.is_admin_or_moderator(msg.get_user_id()) \
                and len(msg.get_text()) > settings.MAX_SEARCH_QUERY_LENGTH:
            await self.reply_error(get_message_too_long_message())
            return False
        return True

    async def _do_handle(self) -> None:
        msg = self._message
        content = msg.get_text().split()
        quote = " ".join(content[1:])

        serial_manager = SerialContextManager(self._logger)
        active_series = await serial_manager.get_user_active_series(msg.get_user_id())

        segments = await TranscriptionFinder.find_segment_by_quote(quote, self._logger, active_series)
        if not segments:
            return await self.__reply_no_segments_found(quote)

        segment = segments[0] if isinstance(segments, list) else segments
        start_time = max(0, segment["start_time"] - settings.EXTEND_BEFORE)
        end_time = segment["end_time"] + settings.EXTEND_AFTER

        clip_duration = end_time - start_time
        if await self._handle_clip_duration_limit_exceeded(clip_duration):
            return None

        try:
            output_filename = await ClipsExtractor.extract_clip(segment["video_path"], start_time, end_time, self._logger)
            await self._responder.send_video(output_filename)
        except FFMpegException as e:
            return await self.__reply_extraction_failed(e)

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
        await self.reply_error(get_no_segments_found_message())
        await self._log_system_message(logging.INFO, get_log_no_segments_found_message(quote))

    async def __reply_extraction_failed(self, exception: FFMpegException) -> None:
        await self.reply_error(get_extraction_failure_message())
        await self._log_system_message(logging.ERROR, get_log_extraction_failure_message(exception))

    async def __log_segment_and_clip_success(self, chat_id: int, username: str) -> None:
        await self._log_system_message(logging.INFO, get_log_segment_saved_message(chat_id))
        await self._log_system_message(logging.INFO, get_log_clip_success_message(username))
