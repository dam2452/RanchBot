import logging
import os
from pathlib import Path
import tempfile
from typing import (
    List,
    Optional,
)

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.sending_videos.saved_clip_thumbnail_handler_responses import (
    get_clip_not_found_message,
    get_invalid_frame_selector_message,
    get_log_clip_not_found_message,
    get_log_keyframe_sent_message,
    get_no_clip_identifier_provided_message,
)
from bot.video.keyframe_extractor import KeyframeExtractor


class SavedClipThumbnailHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["klatkaklipu", "kk"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_clip_existence,
        ]

    def _get_usage_message(self) -> str:
        return get_no_clip_identifier_provided_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, 2)

    async def __check_clip_existence(self) -> bool:
        clip_identifier = self.__get_clip_identifier()
        clip = await self.__resolve_clip(clip_identifier)
        if not clip:
            await self._reply_error(get_clip_not_found_message(clip_identifier))
            await self._log_system_message(
                logging.INFO,
                get_log_clip_not_found_message(clip_identifier, self._message.get_username()),
            )
            return False
        return True

    async def _do_handle(self) -> None:
        content = self._message.get_text().split()
        clip_identifier = content[1]
        frame_selector_raw = content[2] if len(content) >= 3 else "0"

        frame_selector = self.__parse_frame_selector(frame_selector_raw)
        if frame_selector is None:
            return await self._reply_error(get_invalid_frame_selector_message())

        clip = await self.__resolve_clip(clip_identifier)

        fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        video_path = Path(tmp_path)
        try:
            video_path.write_bytes(clip.video_data)

            duration = clip.duration or 0.0
            if clip.end_time > clip.start_time:
                keyframes = await KeyframeExtractor.get_keyframe_timestamps(
                    video_path, clip.start_time, clip.end_time,
                )
            else:
                keyframes = []

            if not keyframes:
                seek_time = clip.start_time if clip.end_time > clip.start_time else duration * 0.1
            else:
                idx = frame_selector if frame_selector >= 0 else len(keyframes) + frame_selector
                idx = max(0, min(idx, len(keyframes) - 1))
                seek_time = keyframes[idx]

            await self._send_keyframe(video_path, seek_time)
        finally:
            video_path.unlink(missing_ok=True)

        await self._log_system_message(
            logging.INFO,
            get_log_keyframe_sent_message(clip_identifier, self._message.get_username()),
        )

    async def __resolve_clip(self, identifier: str):
        user_id = self._message.get_user_id()
        if identifier.isdigit():
            clips = await DatabaseManager.get_saved_clips(user_id)
            index = int(identifier)
            if clips and 1 <= index <= len(clips):
                return clips[index - 1]
            return None
        return await DatabaseManager.get_clip_by_name(user_id, identifier)

    def __get_clip_identifier(self) -> str:
        return self._message.get_text().split()[1]

    @staticmethod
    def __parse_frame_selector(raw: str) -> Optional[int]:
        return KeyframeExtractor.parse_frame_selector(raw)
