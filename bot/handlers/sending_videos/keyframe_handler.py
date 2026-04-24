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
    get_no_frames_for_navigation_message,
    get_no_keyframes_provided_message,
    get_no_last_clip_message,
)
from bot.search.video_frames.frames_finder import VideoFramesFinder
from bot.settings import settings
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
    VideoFrameKeys,
)
from bot.utils.functions import escape_markdown_v2
from bot.video.keyframe_extractor import KeyframeExtractor


class KeyframeHandler(BotMessageHandler):
    __FIRST_ALIASES = frozenset({"p", "pierwsza", "first"})
    __LAST_ALIASES = frozenset({"o", "ostatnia", "last"})

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

        result_index = self.__parse_result_index(content[1] if len(content) >= 2 else "1")
        if result_index is None:
            return await self._reply_error(get_invalid_result_index_message())

        frame_selector = self.__parse_frame_selector(content[2] if len(content) >= 3 else "0")
        if frame_selector is None:
            return await self._reply_error(get_invalid_frame_selector_message())

        segment, start_time, end_time = await self.__resolve_segment_and_times(result_index)
        if segment is None:
            return None

        episode_metadata = segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
        season: Optional[int] = episode_metadata.get(EpisodeMetadataKeys.SEASON)
        episode_number: Optional[int] = episode_metadata.get(EpisodeMetadataKeys.EPISODE_NUMBER)
        series_name: Optional[str] = episode_metadata.get(EpisodeMetadataKeys.SERIES_NAME)

        if season is None or episode_number is None or not series_name:
            return await self._reply_error(get_no_last_clip_message())

        active_series = await self._get_user_active_series(self._message.get_user_id())
        frames = await VideoFramesFinder.find_frames_in_time_range(
            season=season,
            episode_number=episode_number,
            start_time=start_time,
            end_time=end_time,
            series_name=active_series or series_name,
            logger=self._logger,
        )

        if not frames:
            if frame_selector != 0:
                return await self._reply_error(get_no_frames_for_navigation_message())
            seek_time = start_time
            frame_display: Optional[Tuple[int, int]] = None
        else:
            try:
                frame = frames[frame_selector]
            except IndexError:
                return await self._reply_error(get_invalid_frame_index_message(len(frames) - 1))
            seek_time = float(frame[VideoFrameKeys.TIMESTAMP])
            frame_display = (frame_selector % len(frames), len(frames))

        video_path = Path(segment[SegmentKeys.VIDEO_PATH])
        frame_path = await KeyframeExtractor.extract_keyframe(video_path, seek_time)
        caption = self.__build_caption(season, episode_number, seek_time, frame_display)
        await self._responder.send_photo(image_bytes=frame_path.read_bytes(), image_path=frame_path, caption=caption)

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

    @classmethod
    def __parse_result_index(cls, raw: str) -> Optional[int]:
        if not raw.isdigit():
            return None
        val = int(raw)
        return val if val >= 1 else None

    @classmethod
    def __parse_frame_selector(cls, raw: str) -> Optional[int]:
        lower = raw.lower()
        if lower in cls.__FIRST_ALIASES:
            return 0
        if lower in cls.__LAST_ALIASES:
            return -1
        try:
            return int(raw)
        except ValueError:
            return None

    @staticmethod
    def __build_caption(
        season: int,
        episode_number: int,
        seek_time: float,
        frame_display: Optional[Tuple[int, int]],
    ) -> str:
        base = f"S{season:02d}E{episode_number:02d} | {seek_time:.2f}s"
        if frame_display:
            idx, total = frame_display
            return escape_markdown_v2(f"{base} | klatka {idx + 1}/{total}")
        return escape_markdown_v2(base)
