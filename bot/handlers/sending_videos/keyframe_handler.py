import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.sending_videos.keyframe_handler_responses import (
    get_invalid_frame_index_message,
    get_invalid_frame_selector_message,
    get_invalid_result_index_message,
    get_log_keyframe_sent_message,
    get_log_no_last_clip_message,
    get_no_keyframes_provided_message,
    get_no_last_clip_message,
)
from bot.settings import settings
from bot.utils.constants import SegmentKeys
from bot.utils.functions import parse_frame_selector
from bot.video.keyframe_extractor import KeyframeExtractor


class KeyframeHandler(BotMessageHandler):

    def get_commands(self) -> List[str]:
        return ["klatka", "frame", "kl"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_no_keyframes_provided_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 0, 2)

    async def _do_handle(self) -> None:
        content = self._get_message_content()

        if len(content) >= 3:
            result_index = self.__parse_result_index(content[1])
            frame_selector = self.__parse_frame_selector(content[2])
        else:
            result_index = 1
            frame_selector = self.__parse_frame_selector(content[1] if len(content) >= 2 else "0")

        if result_index is None:
            return await self._reply_error(get_invalid_result_index_message())
        if frame_selector is None:
            return await self._reply_error(get_invalid_frame_selector_message())

        segment, start_time, end_time = await self.__resolve_segment_and_times(result_index)
        if segment is None:
            return None

        video_path = Path(segment[SegmentKeys.VIDEO_PATH])

        keyframes = await KeyframeExtractor.get_keyframe_timestamps(video_path, start_time, end_time)
        if not keyframes:
            seek_time = start_time
        else:
            idx = frame_selector if frame_selector >= 0 else len(keyframes) + frame_selector
            if idx < 0 or idx >= len(keyframes):
                return await self._reply_error(get_invalid_frame_index_message(len(keyframes) - 1))
            seek_time = keyframes[idx]

        await self._send_keyframe(video_path, seek_time)

        return await self._log_system_message(
            logging.INFO,
            get_log_keyframe_sent_message(result_index, seek_time, self._message.get_username()),
        )

    async def __resolve_segment_and_times(
        self,
        result_index: int,
    ) -> Tuple[Optional[Dict[str, Any]], float, float]:
        last_search = await DatabaseManager.get_last_search_by_chat_id(self._message.get_chat_id())
        if last_search:
            segments = json.loads(last_search.segments)
            if result_index > len(segments):
                await self._reply_error(get_invalid_result_index_message())
                return None, 0.0, 0.0
            segment = segments[result_index - 1]
            start_time = max(0.0, float(segment[SegmentKeys.START_TIME]) - settings.EXTEND_BEFORE)
            end_time = float(segment[SegmentKeys.END_TIME]) + settings.EXTEND_AFTER
            return segment, start_time, end_time

        last_clip = await DatabaseManager.get_last_clip_by_chat_id(self._message.get_chat_id())
        if not last_clip:
            await self._reply_error(get_no_last_clip_message())
            await self._log_system_message(logging.INFO, get_log_no_last_clip_message())
            return None, 0.0, 0.0
        segment_raw = last_clip.segment
        segment = json.loads(segment_raw) if isinstance(segment_raw, str) else segment_raw
        start_time = last_clip.adjusted_start_time or float(segment.get(SegmentKeys.START_TIME, 0))
        end_time = last_clip.adjusted_end_time or float(segment.get(SegmentKeys.END_TIME, 0))
        return segment, start_time, end_time

    @staticmethod
    def __parse_result_index(raw: str) -> Optional[int]:
        if not raw.isdigit():
            return None
        val = int(raw)
        return val if val >= 1 else None

    @staticmethod
    def __parse_frame_selector(raw: str) -> Optional[int]:
        return parse_frame_selector(raw)
