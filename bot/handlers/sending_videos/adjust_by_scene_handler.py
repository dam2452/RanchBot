import json
import logging
from typing import (
    List,
    Optional,
    Tuple,
)

from bot.database.database_manager import DatabaseManager
from bot.database.models import (
    ClipType,
    LastClip,
)
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.sending_videos.adjust_video_clip_handler_responses import (
    get_invalid_interval_log,
    get_invalid_interval_message,
    get_no_quotes_selected_log,
    get_no_quotes_selected_message,
    get_sd_invalid_args_message,
    get_sd_no_scene_cuts_message,
    get_successful_adjustment_message,
    get_updated_segment_info_log,
)
from bot.services.scene_snap.scene_snap_service import SceneSnapService
from bot.settings import settings
from bot.types import ElasticsearchSegment
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.video.clips_extractor import ClipsExtractor
from bot.video.utils import get_video_duration


class AdjustBySceneHandler(BotMessageHandler):
    __COMMANDS: List[str] = ["sdostosuj", "sadjust", "sd"]

    def get_commands(self) -> List[str]:
        return AdjustBySceneHandler.__COMMANDS

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 2, get_sd_invalid_args_message(), 3)

    async def _do_handle(self) -> None:
        msg = self._message
        content = msg.get_text().split()
        chat_id = msg.get_chat_id()

        last_clip = await DatabaseManager.get_last_clip_by_chat_id(chat_id)
        if not last_clip:
            return await self.__reply_no_last_clip()

        segment_info: ElasticsearchSegment = (
            json.loads(last_clip.segment) if isinstance(last_clip.segment, str) else last_clip.segment
        )

        n_before, n_after = await self.__parse_scene_offsets(content)
        if n_before is None:
            return None

        clip_start, clip_end = AdjustBySceneHandler.__resolve_clip_bounds(last_clip, segment_info)
        active_series = await self._get_user_active_series(msg.get_user_id())

        scene_bounds = await self.__compute_scene_bounds(segment_info, clip_start, clip_end, n_before, n_after, active_series)
        if scene_bounds is None:
            return await self._reply_error(get_sd_no_scene_cuts_message())

        new_start, new_end = scene_bounds
        new_start = max(0.0, new_start)
        video_duration = await get_video_duration(segment_info.get(SegmentKeys.VIDEO_PATH))
        new_end = min(new_end, video_duration)

        if new_start >= new_end:
            await self._reply_error(get_invalid_interval_message())
            await self._log_system_message(logging.INFO, get_invalid_interval_log())
            return None

        if await self._handle_clip_duration_limit_exceeded(new_end - new_start):
            return None

        output_filename = await ClipsExtractor.extract_clip(
            segment_info.get(SegmentKeys.VIDEO_PATH), new_start, new_end, self._logger,
        )
        await self._responder.send_video(
            output_filename,
            duration=new_end - new_start,
            suggestions=["Zmniejszyć liczbę cięć", "Wybrać krótszy fragment"],
        )
        await DatabaseManager.insert_last_clip(
            chat_id=chat_id,
            segment=segment_info,
            compiled_clip=None,
            clip_type=ClipType.ADJUSTED,
            adjusted_start_time=new_start,
            adjusted_end_time=new_end,
            is_adjusted=True,
        )

        await self._log_system_message(logging.INFO, get_updated_segment_info_log(chat_id))
        return await self._log_system_message(logging.INFO, get_successful_adjustment_message(msg.get_username()))

    async def __compute_scene_bounds(
        self,
        segment_info: ElasticsearchSegment,
        clip_start: float,
        clip_end: float,
        n_before: int,
        n_after: int,
        active_series: str,
    ) -> Optional[Tuple[float, float]]:
        episode_metadata = segment_info.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
        season = episode_metadata.get(EpisodeMetadataKeys.SEASON)
        episode_number = episode_metadata.get(EpisodeMetadataKeys.EPISODE_NUMBER)

        if season is None or episode_number is None:
            return None

        scene_cuts = await SceneSnapService.fetch_scene_cuts(active_series, season, episode_number, self._logger)
        if not scene_cuts:
            return None

        new_start = SceneSnapService.find_boundary_by_cut_offset(scene_cuts, clip_start, n_before, "back")
        new_end = SceneSnapService.find_boundary_by_cut_offset(scene_cuts, clip_end, n_after, "forward")
        return new_start, new_end

    @staticmethod
    def __resolve_clip_bounds(
        last_clip: LastClip,
        segment_info: ElasticsearchSegment,
    ) -> Tuple[float, float]:
        clip_start = last_clip.adjusted_start_time
        clip_end = last_clip.adjusted_end_time
        if clip_start is not None and clip_end is not None:
            return clip_start, clip_end
        speech_start = float(segment_info.get(SegmentKeys.START_TIME, 0))
        speech_end = float(segment_info.get(SegmentKeys.END_TIME, 0))
        return max(0.0, speech_start - settings.EXTEND_BEFORE), speech_end + settings.EXTEND_AFTER

    async def __parse_scene_offsets(self, content: List[str]) -> Tuple[Optional[int], Optional[int]]:
        try:
            return int(content[-2]), int(content[-1])
        except ValueError:
            await self._reply_invalid_args_count(get_sd_invalid_args_message())
            return None, None

    async def __reply_no_last_clip(self) -> None:
        await self._reply_error(get_no_quotes_selected_message())
        await self._log_system_message(logging.INFO, get_no_quotes_selected_log())
