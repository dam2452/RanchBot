import logging
import math
import tempfile
from typing import List

from aiogram.exceptions import TelegramEntityTooLarge

from bot.database.database_manager import DatabaseManager
from bot.database.models import ClipType
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.sending_videos.compile_selected_clips_handler_responses import (
    get_compiled_clip_sent_message,
    get_invalid_args_count_message,
    get_log_no_matching_clips_found_message,
    get_no_matching_clips_found_message,
)
from bot.video.clips_compiler import (
    ClipsCompiler,
    process_compiled_clip,
)


class CompileSelectedClipsHandler(BotMessageHandler):
    class ClipNotFoundException(Exception):
        def __init__(self, message: str) -> None:
            self.message = message
            super().__init__(self.message)

    def get_commands(self) -> List[str]:
        return ["połączklipy", "polaczklipy", "concatclips", "pk"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_user_has_clips,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 2, get_invalid_args_count_message(), math.inf)

    async def __check_user_has_clips(self) -> bool:
        user_clips = await DatabaseManager.get_saved_clips(self._message.get_user_id())
        if not user_clips:
            await self.__reply_no_matching_clips_found()
            return False
        return True

    async def _do_handle(self) -> None:
        content = self._message.get_text().split()

        try:
            clip_numbers = [int(clip) for clip in content[1:]]
        except ValueError:
            return await self._reply_invalid_args_count(get_invalid_args_count_message())

        user_clips = await DatabaseManager.get_saved_clips(self._message.get_user_id())

        selected_clips = []
        for clip_number in clip_numbers:
            if 1 <= clip_number <= len(user_clips):
                selected_clips.append(user_clips[clip_number - 1])
            else:
                return await self._reply_invalid_args_count(get_invalid_args_count_message())

        if not selected_clips:
            return await self.__reply_no_matching_clips_found()

        selected_segments = []
        for clip in selected_clips:
            temp_file = tempfile.NamedTemporaryFile(delete=False, delete_on_close=False, suffix=".mp4")
            temp_file.write(clip.video_data)
            temp_file.close()
            selected_segments.append({
                "video_path": temp_file.name,
                "start": 0,
                "end": clip.duration,
            })

        total_duration = sum(clip.duration for clip in selected_clips)

        if await self._handle_clip_duration_limit_exceeded(total_duration):
            return None

        compiled_output = await ClipsCompiler.compile(self._message, selected_segments, self._logger)
        await process_compiled_clip(self._message, compiled_output, ClipType.COMPILED)

        try:
            await self._responder.send_video(compiled_output)
        except TelegramEntityTooLarge:
            await self.handle_telegram_entity_too_large_for_compilation(total_duration)
            return None

        return await self._log_system_message(
            logging.INFO,
            get_compiled_clip_sent_message(self._message.get_username()),
        )

    async def __reply_no_matching_clips_found(self) -> None:
        await self.reply_error(get_no_matching_clips_found_message())
        await self._log_system_message(logging.INFO, get_log_no_matching_clips_found_message())
