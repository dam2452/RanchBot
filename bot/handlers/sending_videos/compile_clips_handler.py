import json
import logging
import math
from typing import (
    Dict,
    List,
    Union,
)

from aiogram.exceptions import TelegramEntityTooLarge

from bot.database.database_manager import DatabaseManager
from bot.database.models import ClipType
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.sending_videos.compile_clips_handler_responses import (
    get_clip_time_message,
    get_invalid_args_count_message,
    get_invalid_index_message,
    get_invalid_range_message,
    get_log_compilation_success_message,
    get_log_compiled_clip_is_too_long_message,
    get_log_invalid_index_message,
    get_log_invalid_range_message,
    get_log_no_matching_segments_found_message,
    get_log_no_previous_search_results_message,
    get_max_clips_exceeded_message,
    get_no_matching_segments_found_message,
    get_no_previous_search_results_message,
    get_selected_clip_message,
)
from bot.settings import settings
from bot.video.clips_compiler import (
    ClipsCompiler,
    process_compiled_clip,
)


class CompileClipsHandler(BotMessageHandler):
    class InvalidRangeException(Exception):
        pass

    class InvalidIndexException(Exception):
        pass

    class NoMatchingSegmentsException(Exception):
        pass

    class MaxClipsExceededException(Exception):
        pass

    def get_commands(self) -> List[str]:
        return ["kompiluj", "compile", "kom"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message,1, get_invalid_args_count_message(), math.inf)

    async def _do_handle(self) -> None:
        content = self._message.get_text().split()
        chat_id = self._message.get_chat_id()
        user_id = self._message.get_user_id()
        username = self._message.get_username()

        last_search = await DatabaseManager.get_last_search_by_chat_id(chat_id)
        if not last_search or not last_search.segments:
            return await self.__reply_no_previous_search_results()

        segments = json.loads(last_search.segments)
        try:
            selected_segments = await self.__parse_segments(content[1:], segments)
        except self.InvalidRangeException as e:
            return await self.__reply_invalid_range(str(e))
        except self.InvalidIndexException as e:
            return await self.__reply_invalid_index(str(e))
        except self.NoMatchingSegmentsException:
            return await self.__reply_no_matching_segments_found()
        except self.MaxClipsExceededException:
            return await self.__reply_max_clips_exceeded()

        if not selected_segments:
            return await self.__reply_no_matching_segments_found()

        if (
            not await DatabaseManager.is_admin_or_moderator(user_id)
            and len(selected_segments) > settings.MAX_CLIPS_PER_COMPILATION
        ):
            return await self.__reply_max_clips_exceeded()

        total_duration = 0
        for segment in selected_segments:
            duration = (segment["end_time"] + settings.EXTEND_AFTER) - (segment["start_time"] - settings.EXTEND_BEFORE)
            total_duration += duration
            await self._log_system_message(
                logging.INFO,
                get_selected_clip_message(segment["video_path"], segment["start_time"], segment["end_time"], duration),
            )

        if await self._check_clip_duration_limit(user_id, total_duration):
            return await self.__reply_clip_duration_exceeded()

        compiled_output = await ClipsCompiler.compile(self._message, selected_segments, self._logger)
        await process_compiled_clip(self._message, compiled_output, ClipType.COMPILED)

        try:
            await self._responder.send_video(compiled_output)
        except TelegramEntityTooLarge:
            await self.handle_telegram_entity_too_large_for_compilation(total_duration)
            return None

        return await self._log_system_message(logging.INFO, get_log_compilation_success_message(username))

    async def __parse_segments(
        self, content: List[str], segments: List[Dict[str, Union[str, float]]],
    ) -> List[Dict[str, Union[str, float]]]:
        selected_segments = []
        for arg in content:
            if arg.lower() in {"all", "wszystko"}:
                selected_segments.extend(
                    {
                        "video_path": s["video_path"],
                        "start_time": s["start_time"],
                        "end_time": s["end_time"],
                    }
                    for s in segments
                )
                return selected_segments
            if "-" in arg:
                selected_segments.extend(await self.__parse_range(arg, segments))
            else:
                selected_segments.append(await self.__parse_single(arg, segments))
        return selected_segments

    async def __parse_range(self, index: str, segments: List[Dict[str, Union[str, float]]]) -> List[Dict[str, Union[str, float]]]:
        user_id = self._message.get_user_id()

        try:
            start_str, end_str = index.split("-")
        except ValueError as exc:
            raise self.InvalidRangeException(get_invalid_range_message(index)) from exc

        try:
            start, end = int(start_str), int(end_str)
        except ValueError as exc:
            raise self.InvalidRangeException(get_invalid_range_message(index)) from exc

        if start > end:
            raise self.InvalidRangeException(get_invalid_range_message(index))

        num_of_clips = end - start + 1
        if not await DatabaseManager.is_admin_or_moderator(user_id) and num_of_clips > settings.MAX_CLIPS_PER_COMPILATION:
            raise self.MaxClipsExceededException()

        collected = []
        for i in range(start, end + 1):
            try:
                segment = segments[i - 1]
                collected.append({
                    "video_path": segment["video_path"],
                    "start_time": segment["start_time"],
                    "end_time": segment["end_time"],
                })
            except IndexError:
                pass

        if not collected:
            raise self.NoMatchingSegmentsException()
        return collected

    async def __parse_single(self, index_str: str, segments: List[Dict[str, Union[str, float]]]) -> Dict[str, Union[str, float]]:
        try:
            idx = int(index_str)
        except ValueError as exc:
            raise self.InvalidIndexException(get_invalid_index_message(index_str)) from exc

        if idx < 1 or idx > len(segments):
            raise self.NoMatchingSegmentsException()

        segment = segments[idx - 1]
        return {
            "video_path": segment["video_path"],
            "start_time": segment["start_time"],
            "end_time": segment["end_time"],
        }

    @staticmethod
    async def _check_clip_duration_limit(user_id: int, total_duration: float) -> bool:
        if await DatabaseManager.is_admin_or_moderator(user_id):
            return False
        return total_duration > settings.LIMIT_DURATION

    async def __reply_no_previous_search_results(self) -> None:
        await self.reply_error(get_no_previous_search_results_message())
        await self._log_system_message(logging.INFO, get_log_no_previous_search_results_message())

    async def __reply_no_matching_segments_found(self) -> None:
        await self.reply_error(get_no_matching_segments_found_message())
        await self._log_system_message(logging.INFO, get_log_no_matching_segments_found_message())

    async def __reply_clip_duration_exceeded(self) -> None:
        await self.reply_error(get_clip_time_message())
        await self._log_system_message(
            logging.INFO,
            get_log_compiled_clip_is_too_long_message(self._message.get_username()),
        )

    async def __reply_invalid_range(self, err_msg: str) -> None:
        await self.reply_error(err_msg)
        await self._log_system_message(logging.INFO, get_log_invalid_range_message())

    async def __reply_invalid_index(self, err_msg: str) -> None:
        await self.reply_error(err_msg)
        await self._log_system_message(logging.INFO, get_log_invalid_index_message())

    async def __reply_max_clips_exceeded(self) -> None:
        await self.reply_error(get_max_clips_exceeded_message())
        await self._log_system_message(logging.INFO, get_max_clips_exceeded_message())
