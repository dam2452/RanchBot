import logging
import math
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
from bot.responses.sending_videos.send_clip_handler_responses import (
    get_clip_not_found_message,
    get_empty_clip_file_message,
    get_empty_file_error_message,
    get_give_clip_name_message,
    get_log_clip_not_found_message,
    get_log_clip_sent_message,
    get_log_empty_clip_file_message,
    get_log_empty_file_error_message,
)


class SendClipHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["wyślij", "wyslij", "send", "wys"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_clip_existence,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_give_clip_name_message(), math.inf)

    async def __check_clip_existence(self) -> bool:
        content = self._message.get_text().split()
        clip_identifier = " ".join(content[1:])
        user_id = self._message.get_user_id()

        clips = await DatabaseManager.get_saved_clips(user_id) or []

        if clip_identifier.isdigit():
            clip_number = int(clip_identifier)
            if clip_number < 1 or clip_number > len(clips):
                await self.__reply_clip_not_found(clip_number)
                return False
        else:
            clip = await DatabaseManager.get_clip_by_name(user_id, clip_identifier)
            if not clip:
                await self.__reply_clip_not_found(None)
                return False

        return True

    async def _do_handle(self) -> None:
        content = self._message.get_text().split()
        clip_identifier = " ".join(content[1:])
        user_id = self._message.get_user_id()

        if clip_identifier.isdigit():
            clip_number = int(clip_identifier)
            clips = await DatabaseManager.get_saved_clips(user_id)
            clip = clips[clip_number - 1]
        else:
            clip = await DatabaseManager.get_clip_by_name(user_id, clip_identifier)

        if await self._handle_clip_duration_limit_exceeded(clip.duration):
            return None

        video_data = clip.video_data
        if not video_data:
            return await self.__reply_empty_clip_file(clip.name)

        temp_file_path = Path(tempfile.gettempdir()) / f"{clip.name}.mp4"
        with temp_file_path.open("wb") as temp_file:
            temp_file.write(video_data)

        if temp_file_path.stat().st_size == 0:
            return await self.__reply_empty_file_error(clip.name)

        await self._responder.send_video(
            temp_file_path,
            duration=clip.duration,
            suggestions=["Wybrać krótszy fragment"],
        )

        return await self._log_system_message(
            logging.INFO,
            get_log_clip_sent_message(clip.name, self._message.get_username()),
        )

    async def __reply_clip_not_found(self, clip_number: Optional[int]) -> None:
        await self._reply_error(get_clip_not_found_message(clip_number))
        await self._log_system_message(
            logging.INFO,
            get_log_clip_not_found_message(clip_number, self._message.get_username()),
        )

    async def __reply_empty_clip_file(self, clip_name: str) -> None:
        await self._reply_error(get_empty_clip_file_message())
        await self._log_system_message(
            logging.WARNING,
            get_log_empty_clip_file_message(clip_name, self._message.get_username()),
        )

    async def __reply_empty_file_error(self, clip_name: str) -> None:
        await self._reply_error(get_empty_file_error_message())
        await self._log_system_message(
            logging.ERROR,
            get_log_empty_file_error_message(clip_name, self._message.get_username()),
        )
