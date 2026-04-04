import json
import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.models import (
    ClipType,
    LastClip,
)
from bot.handlers.bot_message_handler import BotMessageHandler
from bot.responses.sending_videos.tiktak_handler_responses import (
    get_no_last_clip_message,
    get_tiktak_compiled_note,
    get_tiktak_no_detections_note,
    get_tiktak_success_log,
)
from bot.settings import settings
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.video.tiktak_processor import TikTakProcessor


class TikTakHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["tiktak", "tt"]

    async def _do_handle(self) -> None:
        msg = self._message
        chat_id = msg.get_chat_id()

        last_clip = await DatabaseManager.get_last_clip_by_chat_id(chat_id)
        if not last_clip:
            return await self._reply_error(get_no_last_clip_message())

        if last_clip.clip_type == ClipType.COMPILED and last_clip.compiled_clip:
            return await self.__handle_compiled(last_clip)

        return await self.__handle_single(last_clip)

    async def __handle_compiled(self, last_clip: LastClip) -> None:
        output = await TikTakProcessor.process_compiled(
            last_clip.compiled_clip,
            self._logger,
        )
        await self._responder.send_markdown(get_tiktak_compiled_note())
        await self._responder.send_video(output, duration=None)
        await DatabaseManager.insert_last_clip(
            chat_id=self._message.get_chat_id(),
            segment=json.loads(last_clip.segment) if isinstance(last_clip.segment, str) else last_clip.segment,
            compiled_clip=None,
            clip_type=ClipType.TIKTAK,
            adjusted_start_time=last_clip.adjusted_start_time,
            adjusted_end_time=last_clip.adjusted_end_time,
            is_adjusted=last_clip.is_adjusted,
        )
        return await self._log_system_message(
            logging.INFO,
            get_tiktak_success_log(self._message.get_username()),
        )

    async def __handle_single(self, last_clip: LastClip) -> None:
        segment = json.loads(last_clip.segment) if isinstance(last_clip.segment, str) else last_clip.segment
        video_path = segment.get(SegmentKeys.VIDEO_PATH)
        start_time = last_clip.adjusted_start_time or float(segment.get(SegmentKeys.START_TIME, 0))
        end_time = last_clip.adjusted_end_time or float(segment.get(SegmentKeys.END_TIME, 0))

        episode_metadata = segment.get(EpisodeMetadataKeys.EPISODE_METADATA, {})
        season = episode_metadata.get(EpisodeMetadataKeys.SEASON)
        episode_number = episode_metadata.get(EpisodeMetadataKeys.EPISODE_NUMBER)
        series_name = episode_metadata.get(EpisodeMetadataKeys.SERIES_NAME, "")

        had_detections = self.__has_detections(
            series_name, season, episode_number, settings.TIKTAK_DETECTION_DIR,
        )

        output = await TikTakProcessor.process_single(
            video_path=video_path,
            start_time=start_time,
            end_time=end_time,
            season=season or 0,
            episode_number=episode_number or 0,
            series_name=series_name,
            detection_dir=settings.TIKTAK_DETECTION_DIR,
            logger=self._logger,
        )

        if not had_detections:
            await self._responder.send_markdown(get_tiktak_no_detections_note())

        duration = end_time - start_time
        await self._responder.send_video(output, duration=duration)

        await DatabaseManager.insert_last_clip(
            chat_id=self._message.get_chat_id(),
            segment=segment,
            compiled_clip=None,
            clip_type=ClipType.TIKTAK,
            adjusted_start_time=start_time,
            adjusted_end_time=end_time,
            is_adjusted=last_clip.is_adjusted,
        )
        return await self._log_system_message(
            logging.INFO,
            get_tiktak_success_log(self._message.get_username()),
        )

    @staticmethod
    def __has_detections(
        series_name: str,
        season: int,
        episode_number: int,
        detection_dir: str,
    ) -> bool:
        if season is None or episode_number is None:
            return False
        det_path = TikTakProcessor._detection_file_path(series_name, season, episode_number, detection_dir)
        return det_path is not None and det_path.exists()
