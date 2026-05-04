import json
import logging
from typing import (
    List,
    Optional,
    Tuple,
)

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.sending_videos.save_clip_by_index_handler_responses import (
    get_clip_limit_exceeded_message,
    get_clip_name_exists_message,
    get_clip_name_length_exceeded_message,
    get_clip_name_numeric_message,
    get_clip_saved_successfully_message,
    get_invalid_adjust_format_message,
    get_invalid_segment_number_message,
    get_log_clip_name_exists_message,
    get_log_clip_name_numeric_message,
    get_log_clip_saved_successfully_message,
    get_log_invalid_adjust_format_message,
    get_log_invalid_segment_number_message,
    get_log_no_previous_search_message,
    get_no_previous_search_message,
    get_usage_message,
)
from bot.services.scene_snap.scene_snap_service import SceneSnapService
from bot.settings import settings
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.video.clips_extractor import ClipsExtractor
from bot.video.utils import get_video_duration


class SaveClipByIndexHandler(BotMessageHandler):

    def get_commands(self) -> List[str]:
        return ["zapisznumer", "zn"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_last_search_exists,
            self.__check_segment_number,
            self.__check_adjust_format,
            self.__check_clip_name_format,
            self.__check_clip_name_length,
            self.__check_clip_name_unique,
            self.__check_clip_limit_not_exceeded,
        ]

    def _get_usage_message(self) -> str:
        return get_usage_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 2, 4)

    async def __check_last_search_exists(self) -> bool:
        last_search = await DatabaseManager.get_last_search_by_chat_id(self._message.get_chat_id())
        if not last_search:
            await self._reply_error(get_no_previous_search_message())
            await self._log_system_message(logging.INFO, get_log_no_previous_search_message())
            return False
        return True

    async def __check_segment_number(self) -> bool:
        index = self.__parse_segment_index()
        if index is None:
            return False

        last_search = await DatabaseManager.get_last_search_by_chat_id(self._message.get_chat_id())
        segments = json.loads(last_search.segments)

        if index < 1 or index > len(segments):
            await self._reply_error(get_invalid_segment_number_message(index))
            await self._log_system_message(logging.WARNING, get_log_invalid_segment_number_message(index))
            return False
        return True

    async def __check_adjust_format(self) -> bool:
        parsed = self.__parse_args()
        if parsed is None:
            await self._reply_error(get_invalid_adjust_format_message())
            await self._log_system_message(logging.INFO, get_log_invalid_adjust_format_message())
            return False
        return True

    async def __check_clip_name_format(self) -> bool:
        parsed = self.__parse_args()
        if parsed is None:
            return False
        _, _, _, clip_name = parsed
        if clip_name.isdigit():
            await self._reply_error(get_clip_name_numeric_message())
            await self._log_system_message(
                logging.INFO,
                get_log_clip_name_numeric_message(clip_name, self._message.get_username()),
            )
            return False
        return True

    async def __check_clip_name_length(self) -> bool:
        parsed = self.__parse_args()
        if parsed is None:
            return False
        _, _, _, clip_name = parsed
        if len(clip_name) > settings.MAX_CLIP_NAME_LENGTH:
            await self._reply_error(get_clip_name_length_exceeded_message())
            return False
        return True

    async def __check_clip_name_unique(self) -> bool:
        parsed = self.__parse_args()
        if parsed is None:
            return False
        _, _, _, clip_name = parsed
        if not await DatabaseManager.is_clip_name_unique(self._message.get_chat_id(), clip_name):
            await self._reply_error(get_clip_name_exists_message(clip_name))
            await self._log_system_message(
                logging.INFO,
                get_log_clip_name_exists_message(clip_name, self._message.get_username()),
            )
            return False
        return True

    async def __check_clip_limit_not_exceeded(self) -> bool:
        is_admin_or_moderator = await DatabaseManager.is_admin_or_moderator(self._message.get_user_id())
        user_clip_count = await DatabaseManager.get_user_clip_count(self._message.get_chat_id())

        if is_admin_or_moderator or user_clip_count < settings.MAX_CLIPS_PER_USER:
            return True

        await self._reply_error(get_clip_limit_exceeded_message())
        return False

    def __parse_args(self) -> Optional[Tuple[int, float, float, str]]:
        content = self._message.get_text().split()
        parts = content[1:]

        if len(parts) < 2 or len(parts) > 4:
            return None

        if not parts[0].lstrip("-").isdigit():
            return None
        index = int(parts[0])

        if len(parts) == 2:
            return index, 0.0, 0.0, parts[1]

        if len(parts) == 4:
            try:
                left_adj = float(parts[1])
                right_adj = float(parts[2])
            except ValueError:
                return None
            return index, left_adj, right_adj, parts[3]

        return None

    def __parse_segment_index(self) -> Optional[int]:
        content = self._message.get_text().split()
        if len(content) < 2:
            return None
        raw = content[1].lstrip("-")
        if not raw.isdigit():
            return None
        return int(content[1])

    async def _do_handle(self) -> None:
        index, left_adj, right_adj, clip_name = self.__parse_args()

        last_search = await DatabaseManager.get_last_search_by_chat_id(self._message.get_chat_id())
        segments = json.loads(last_search.segments)
        segment = segments[index - 1]

        active_series = await self._get_user_active_series(self._message.get_user_id())
        start_time, end_time = await self.__compute_clip_bounds(segment, active_series)

        start_time, end_time = self.__apply_adjustments(start_time, end_time, left_adj, right_adj)
        start_time, end_time, _ = await self._trim_clip_if_needed(
            start_time=start_time, end_time=end_time, segment_id=index,
        )

        output_filename = await ClipsExtractor.extract_clip(
            segment[SegmentKeys.VIDEO_PATH], start_time, end_time, self._logger,
        )

        with output_filename.open("rb") as f:
            video_data = f.read()

        duration = await get_video_duration(output_filename)

        episode_info = segment.get(
            EpisodeMetadataKeys.EPISODE_METADATA,
            segment.get(EpisodeMetadataKeys.EPISODE_INFO, {}),
        )
        season = episode_info.get(EpisodeMetadataKeys.SEASON)
        episode_number = episode_info.get(EpisodeMetadataKeys.EPISODE_NUMBER)

        await DatabaseManager.save_clip(
            chat_id=self._message.get_chat_id(),
            user_id=self._message.get_user_id(),
            clip_name=clip_name,
            video_data=video_data,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            is_compilation=False,
            season=season,
            episode_number=episode_number,
        )

        await self._reply(
            get_clip_saved_successfully_message(clip_name),
            data={"clip_name": clip_name, "duration": duration},
        )
        await self._log_system_message(
            logging.INFO,
            get_log_clip_saved_successfully_message(clip_name, self._message.get_username()),
        )

    async def __compute_clip_bounds(self, segment, series_name: str) -> Tuple[float, float]:
        start_time = max(0, segment[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE)
        end_time = segment[SegmentKeys.END_TIME] + settings.EXTEND_AFTER

        start_time, end_time = await SceneSnapService.snap_clip_times(
            series_name, segment, start_time, end_time, self._logger,
        )
        return start_time, end_time

    @staticmethod
    def __apply_adjustments(
        start_time: float, end_time: float, left_adj: float, right_adj: float,
    ) -> Tuple[float, float]:
        new_start = start_time - left_adj
        new_end = end_time + right_adj
        return max(0.0, new_start), max(new_start, new_end)
