import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Union,
)

from bot.database.database_manager import DatabaseManager
from bot.database.models import ClipType
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.sending_videos.snap_clip_handler_responses import (
    get_already_snapped_message,
    get_no_adjusted_times_message,
    get_no_last_clip_message,
    get_no_scene_cuts_message,
    get_snap_success_log,
    get_snap_success_message,
)
from bot.services.scene_snap.scene_snap_service import SceneSnapService
from bot.types import ElasticsearchSegment
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.video.clips_extractor import ClipsExtractor


class SnapClipHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["snap", "dopasuj", "sp"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    async def _do_handle(self) -> None:
        msg = self._message
        chat_id = msg.get_chat_id()

        last_clip = await DatabaseManager.get_last_clip_by_chat_id(chat_id)
        if not last_clip:
            return await self._reply_error(get_no_last_clip_message())

        if last_clip.adjusted_start_time is None or last_clip.adjusted_end_time is None:
            return await self._reply_error(get_no_adjusted_times_message())

        segment_raw = last_clip.segment
        segment: Union[ElasticsearchSegment, Dict[str, Any]]
        if isinstance(segment_raw, str):
            segment = json.loads(segment_raw)
        else:
            segment = segment_raw

        speech_start = float(segment.get(SegmentKeys.START_TIME, last_clip.adjusted_start_time))
        speech_end = float(segment.get(SegmentKeys.END_TIME, last_clip.adjusted_end_time))
        clip_start = last_clip.adjusted_start_time
        clip_end = last_clip.adjusted_end_time

        active_series = await self._get_user_active_series(msg.get_user_id())
        episode_metadata = segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
        season = episode_metadata.get(EpisodeMetadataKeys.SEASON)
        episode_number = episode_metadata.get(EpisodeMetadataKeys.EPISODE_NUMBER)

        if season is None or episode_number is None:
            return await self._reply_error(get_no_adjusted_times_message())

        scene_cuts = await SceneSnapService.fetch_scene_cuts(active_series, season, episode_number, self._logger)
        if not scene_cuts:
            return await self._reply_error(get_no_scene_cuts_message())

        snapped_start, snapped_end = SceneSnapService.snap_boundaries(
            clip_start, clip_end, speech_start, speech_end, scene_cuts,
        )

        if snapped_start == clip_start and snapped_end == clip_end:
            return await self._reply(get_already_snapped_message())

        clip_duration = snapped_end - snapped_start
        if await self._handle_clip_duration_limit_exceeded(clip_duration):
            return None

        output_filename = await ClipsExtractor.extract_clip(
            Path(segment[SegmentKeys.VIDEO_PATH]), snapped_start, snapped_end, self._logger,
        )

        await self._responder.send_video(output_filename, duration=clip_duration)

        await DatabaseManager.insert_last_clip(
            chat_id=chat_id,
            segment=segment,
            compiled_clip=None,
            clip_type=ClipType.ADJUSTED,
            adjusted_start_time=snapped_start,
            adjusted_end_time=snapped_end,
            is_adjusted=True,
        )

        await self._reply(get_snap_success_message(clip_start, clip_end, snapped_start, snapped_end))
        return await self._log_system_message(logging.INFO, get_snap_success_log(msg.get_username()))
