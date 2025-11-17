import json
import logging
from pathlib import Path
import tempfile
from typing import (
    Awaitable,
    Callable,
    Dict,
    List,
)

from bot.database.database_manager import DatabaseManager
from bot.database.models import (
    ClipInfo,
    ClipType,
    LastClip,
)
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.save_clip_handler_responses import (
    get_log_clip_name_exists_message,
    get_log_clip_name_numeric_message,
    get_log_clip_saved_successfully_message,
    get_log_no_segment_selected_message,
)
from bot.settings import settings
from bot.video.clips_extractor import ClipsExtractor
from bot.video.utils import get_video_duration


class SaveClipHandler(BotMessageHandler):

    def get_commands(self) -> List[str]:
        return ["zapisz", "save", "z"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_clip_name_format,
            self.__check_clip_name_length,
            self.__check_clip_name_unique,
            self.__check_clip_limit_not_exceeded,
            self.__check_last_clip_exists,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message,
            1,
            await self.get_response(RK.CLIP_NAME_NOT_PROVIDED),
        )

    async def __check_clip_name_format(self) -> bool:
        parts = self._message.get_text().split(maxsplit=1)
        clip_name = parts[1]

        if clip_name.isdigit():
            await self.reply_error(RK.CLIP_NAME_CANNOT_BE_NUMERIC)
            log_message = get_log_clip_name_numeric_message(clip_name, self._message.get_username())
            await self._log_system_message(logging.INFO, log_message)
            return False
        return True

    async def __check_clip_name_length(self) -> bool:
        clip_name = self._message.get_text().split(maxsplit=1)[1]
        if len(clip_name) > settings.MAX_CLIP_NAME_LENGTH:
            await self.reply_error(RK.CLIP_NAME_LENGTH_EXCEEDED)
            return False
        return True

    async def __check_clip_name_unique(self) -> bool:
        clip_name = self._message.get_text().split(maxsplit=1)[1]
        if not await DatabaseManager.is_clip_name_unique(self._message.get_chat_id(), clip_name):
            await self.__reply_clip_name_exists(clip_name)
            return False
        return True

    async def __check_clip_limit_not_exceeded(self) -> bool:
        is_admin_or_moderator = await DatabaseManager.is_admin_or_moderator(self._message.get_user_id())
        user_clip_count = await DatabaseManager.get_user_clip_count(self._message.get_chat_id())

        if is_admin_or_moderator or user_clip_count < settings.MAX_CLIPS_PER_USER:
            return True

        await self.reply_error(RK.CLIP_LIMIT_EXCEEDED)
        return False

    async def __check_last_clip_exists(self) -> bool:
        last_clip = await DatabaseManager.get_last_clip_by_chat_id(self._message.get_chat_id())
        if not last_clip:
            await self.__reply_no_segment_selected()
            return False
        return True

    async def _do_handle(self) -> None:
        clip_name = self._message.get_text().split(maxsplit=1)[1]
        last_clip = await DatabaseManager.get_last_clip_by_chat_id(self._message.get_chat_id())

        clip_info = await self.__prepare_clip(last_clip)

        with clip_info.output_filename.open("rb") as f:
            video_data = f.read()

        duration = await get_video_duration(clip_info.output_filename)

        await DatabaseManager.save_clip(
            chat_id=self._message.get_chat_id(),
            user_id=self._message.get_user_id(),
            clip_name=clip_name,
            video_data=video_data,
            start_time=clip_info.start_time,
            end_time=clip_info.end_time,
            duration=duration,
            is_compilation=clip_info.is_compilation,
            season=clip_info.season,
            episode_number=clip_info.episode_number,
        )

        await self.__reply_clip_saved_successfully(clip_name)

    async def __prepare_clip(self, last_clip: LastClip) -> ClipInfo:
        segment_json = json.loads(last_clip.segment)
        episode_info = segment_json.get("episode_info", {})
        season = episode_info.get("season")
        episode_number = episode_info.get("episode_number")

        clip_handlers: Dict[ClipType, Callable[[], Awaitable[ClipInfo]]] = {
            ClipType.COMPILED: lambda: self.__handle_compiled_clip(last_clip),
            ClipType.ADJUSTED: lambda: self.__handle_adjusted_clip(last_clip, segment_json, season, episode_number),
            ClipType.MANUAL: lambda: self.__handle_manual_clip(segment_json, season, episode_number),
            ClipType.SELECTED: lambda: self.__handle_selected_clip(last_clip, segment_json, season, episode_number),
            ClipType.SINGLE: lambda: self.__handle_single_clip(last_clip, segment_json, season, episode_number),
        }

        if last_clip.clip_type not in clip_handlers:
            raise ValueError(f"Unsupported clip type: {last_clip.clip_type}")

        return await clip_handlers[last_clip.clip_type]()


    async def __handle_compiled_clip(self, last_clip: LastClip) -> ClipInfo:
        output_filename = self.__bytes_to_filepath(last_clip.compiled_clip)
        return ClipInfo(
            output_filename=output_filename,
            start_time=0.0,
            end_time=0.0,
            is_compilation=True,
            season=None,
            episode_number=None,
        )


    async def __handle_adjusted_clip(self, last_clip: LastClip, segment_json: dict, season, episode_number) -> ClipInfo:
        output_filename = await ClipsExtractor.extract_clip(
            segment_json["video_path"], last_clip.adjusted_start_time, last_clip.adjusted_end_time, self._logger,
        )
        return ClipInfo(output_filename, last_clip.adjusted_start_time, last_clip.adjusted_end_time, False, season, episode_number)


    async def __handle_manual_clip(self, segment_json: dict, season, episode_number) -> ClipInfo:
        start = segment_json["start"]
        end = segment_json["end"]
        output_filename = await ClipsExtractor.extract_clip(segment_json["video_path"], start, end, self._logger)
        return ClipInfo(output_filename, start, end, False, season, episode_number)


    async def __handle_selected_clip(self, last_clip: LastClip, segment_json: dict, season, episode_number) -> ClipInfo:
        output_filename = await ClipsExtractor.extract_clip(
            segment_json["video_path"], last_clip.adjusted_start_time, last_clip.adjusted_end_time, self._logger,
        )
        return ClipInfo(output_filename, last_clip.adjusted_start_time, last_clip.adjusted_end_time, False, season, episode_number)


    async def __handle_single_clip(self, last_clip: LastClip, segment_json: dict, season, episode_number) -> ClipInfo:
        output_filename = await ClipsExtractor.extract_clip(
            segment_json["video_path"], last_clip.adjusted_start_time, last_clip.adjusted_end_time, self._logger,
        )
        return ClipInfo(output_filename, last_clip.adjusted_start_time, last_clip.adjusted_end_time, False, season, episode_number)


    @staticmethod
    def __bytes_to_filepath(clip_data: bytes) -> Path:
        with tempfile.NamedTemporaryFile(delete=False, delete_on_close=False, suffix=".mp4") as tmp_file:
            path = Path(tmp_file.name)
        path.write_bytes(clip_data)
        return path


    async def __reply_clip_name_exists(self, clip_name: str) -> None:
        await self.reply_error(RK.CLIP_NAME_EXISTS, args=[clip_name])
        await self._log_system_message(logging.INFO, get_log_clip_name_exists_message(clip_name, self._message.get_username()))

    async def __reply_no_segment_selected(self) -> None:
        await self.reply_error(RK.NO_SEGMENT_SELECTED)
        await self._log_system_message(logging.INFO, get_log_no_segment_selected_message())

    async def __reply_clip_saved_successfully(self, clip_name: str) -> None:
        await self.reply(RK.CLIP_SAVED_SUCCESSFULLY, args=[clip_name])
        await self._log_system_message(logging.INFO, get_log_clip_saved_successfully_message(clip_name, self._message.get_username()))
