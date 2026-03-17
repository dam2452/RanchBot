from abc import (
    ABC,
    abstractmethod,
)
import json
import logging
from pathlib import Path
import tempfile
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)

from bot.adapters.rest.models import ResponseStatus as RS
from bot.database.database_manager import DatabaseManager
from bot.database.models import ClipType
from bot.exceptions import (
    CompilationTooLargeException,
    VideoTooLargeException,
)
from bot.interfaces.message import AbstractMessage
from bot.interfaces.responder import AbstractResponder
from bot.responses.bot_message_handler_responses import (
    get_extraction_failure_message,
    get_general_error_message,
    get_invalid_args_count_message,
    get_log_clip_duration_exceeded_message,
    get_log_clip_too_large_message,
    get_log_compilation_too_large_message,
    get_log_extraction_failure_message,
    get_no_video_path_message,
)
from bot.responses.sending_videos.manual_clip_handler_responses import get_limit_exceeded_clip_duration_message
from bot.services.scene_snap.scene_snap_service import SceneSnapService
from bot.services.serial_context.serial_context_manager import SerialContextManager
from bot.settings import settings
from bot.types import ClipSegment
from bot.utils.constants import SegmentKeys
from bot.utils.log import (
    log_system_message,
    log_user_activity,
)
from bot.video.clips_compiler import (
    ClipsCompiler,
    process_compiled_clip,
)
from bot.video.clips_extractor import ClipsExtractor
from bot.video.utils import FFMpegException

ValidatorFunctions = List[Callable[[], Awaitable[bool]]]

class BotMessageHandler(ABC):
    def __init__(self, message: Optional[AbstractMessage], responder: Optional[AbstractResponder], logger: logging.Logger):
        self._message = message
        self._responder = responder
        self._logger = logger
        self._serial_manager = SerialContextManager(logger)

    async def handle(self) -> None:
        await self._log_user_activity(self._message.get_user_id(), self._message.get_text())

        try:
            validators = await self._get_validator_functions()
            for validator in validators:
                if not await validator():
                    return

            await self._do_handle()
        except VideoTooLargeException as e:
            await self._handle_video_too_large_exception(e)
        except CompilationTooLargeException as e:
            await self._handle_compilation_too_large_exception(e)
        except FFMpegException as e:
            await self._handle_ffmpeg_exception(e)
        except json.JSONDecodeError as e:
            await self._reply_error("Wystąpił problem z odczytem danych.")
            await self._log_system_message(
                logging.ERROR,
                f"Data corruption in {self.__get_action_name()}: {e}",
            )
        except Exception as e:
            await self._responder.send_text(get_general_error_message())
            await self._log_system_message(
                logging.ERROR,
                f"{type(e)} Error in {self.__get_action_name()} for user '{self._message.get_user_id()}': {e}",
            )

        await DatabaseManager.log_command_usage(self._message.get_user_id())

    async def _log_system_message(self, level: int, message: str) -> None:
        await log_system_message(level, message, self._logger)

    async def _log_user_activity(self, user_id: int, message: str) -> None:
        await log_user_activity(user_id, message, self._logger)

    async def _get_user_active_series(self, user_id: int) -> str:
        return await self._serial_manager.get_user_active_series(user_id)

    async def _get_user_active_series_id(self, user_id: int) -> int:
        active_series = await self._get_user_active_series(user_id)
        return await DatabaseManager.get_or_create_series(active_series)

    async def _reply_invalid_args_count(self, response: str) -> None:
        await self._responder.send_markdown(response)
        await self._log_system_message(logging.INFO, get_invalid_args_count_message(self.__get_action_name(), self._message.get_user_id()))

    def __get_action_name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def get_commands(self) -> List[str]:
        pass

    @abstractmethod
    async def _do_handle(self) -> None:
        pass


    @abstractmethod
    async def _get_validator_functions(self) -> ValidatorFunctions:
        pass

    async def _handle_clip_duration_limit_exceeded(self, clip_duration: Optional[float]) -> bool:
        if clip_duration is None:
            return False
        if not await DatabaseManager.is_admin_or_moderator(self._message.get_user_id()) and clip_duration > settings.MAX_CLIP_DURATION:
            await self._responder.send_markdown(get_limit_exceeded_clip_duration_message())
            await self._log_system_message(logging.INFO, get_log_clip_duration_exceeded_message(self._message.get_user_id()))
            return True
        return False

    def _get_usage_message(self) -> str:
        return ""

    async def _validate_user_id_is_digit(self) -> bool:
        user_input = self._message.get_text().split()[1]
        if not user_input.isdigit():
            await self._reply_invalid_args_count(self._get_usage_message())
            return False
        return True

    async def _validate_argument_count(
            self,
            message: AbstractMessage,
            min_args: int,
            max_args: Optional[Union[int, float]] = None,
    ) -> bool:
        if max_args is None:
            max_args = min_args

        if min_args <= (len(message.get_text().split()) - 1) <= max_args:
            return True

        await self._reply_invalid_args_count(self._get_usage_message())
        return False

    async def _reply(
            self,
            message: str,
            data: Optional[Dict[str, Any]] = None,
            status: RS = RS.SUCCESS,
    ) -> None:
        if self._message.should_reply_json():
            response_data: Dict[str, Any] = {
                "status": status,
                "message": message,
            }
            if data:
                response_data["data"] = data
            await self._responder.send_json(response_data)
        else:
            await self._responder.send_markdown(message)

    async def _reply_error(self, message: str, data: Optional[Dict[str, Any]] = None):
        await self._reply(message, data, RS.ERROR)

    async def _handle_ffmpeg_exception(self, exception: FFMpegException) -> None:
        await self._reply_error(get_extraction_failure_message())
        await self._log_system_message(logging.ERROR, get_log_extraction_failure_message(exception))

    async def _handle_video_too_large_exception(self, exception: VideoTooLargeException) -> None:
        await self._responder.send_text(self.__get_file_too_large_message(exception.duration, exception.suggestions))
        await self._log_system_message(
            logging.WARNING,
            get_log_clip_too_large_message(exception.duration, self._message.get_username()),
        )

    async def _handle_compilation_too_large_exception(self, exception: CompilationTooLargeException) -> None:
        await self._responder.send_text(self.__get_file_too_large_message(exception.total_duration, exception.suggestions))
        await self._log_system_message(
            logging.WARNING,
            get_log_compilation_too_large_message(exception.total_duration, self._message.get_username()),
        )

    @staticmethod
    def __get_file_too_large_message(duration: Optional[float] = None, suggestions: Optional[List[str]] = None) -> str:
        message = "Plik jest za duży do wysłania"

        if duration is not None:
            message += f" ({duration:.1f}s)"

        message += ".\n\nTelegram ma limit 50MB dla wideo."

        if suggestions:
            message += "\n\nSpróbuj:\n" + "\n".join(f"• {s}" for s in suggestions)

        return message

    async def _send_top_segment_as_clip(
        self,
        top_segment: Dict[str, Any],
        series_name: str,
    ) -> bool:
        if not top_segment.get(SegmentKeys.VIDEO_PATH):
            await self._reply_error(get_no_video_path_message())
            return True

        start_time = max(0, top_segment[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE)
        end_time = top_segment[SegmentKeys.END_TIME] + settings.EXTEND_AFTER

        start_time, end_time = await SceneSnapService.snap_clip_times(
            series_name, top_segment, start_time, end_time, self._logger,
        )

        clip_duration = end_time - start_time
        if await self._handle_clip_duration_limit_exceeded(clip_duration):
            return True

        output_filename = await ClipsExtractor.extract_clip(
            top_segment[SegmentKeys.VIDEO_PATH], start_time, end_time, self._logger,
        )

        await self._responder.send_video(
            output_filename,
            duration=clip_duration,
            suggestions=["Uzyj /w N aby wybrac inny wynik"],
        )

        await DatabaseManager.insert_last_clip(
            chat_id=self._message.get_chat_id(),
            segment=top_segment,
            compiled_clip=None,
            clip_type=ClipType.SINGLE,
            adjusted_start_time=start_time,
            adjusted_end_time=end_time,
            is_adjusted=False,
        )

        return False

    async def _compile_and_send_video(
        self,
        selected_segments: List[ClipSegment],
        total_duration: float,
        clip_type: ClipType,
        series_name: Optional[str] = None,
    ) -> None:
        compiled_output = await ClipsCompiler.compile(self._message, selected_segments, self._logger, series_name)
        await process_compiled_clip(self._message, compiled_output, clip_type)

        try:
            await self._responder.send_video(
                compiled_output,
                duration=total_duration,
                suggestions=["Wybrać mniej klipów", "Wybrać krótsze fragmenty"],
            )
        except VideoTooLargeException as e:
            raise CompilationTooLargeException(total_duration=total_duration, suggestions=e.suggestions) from e

    async def _send_document(self, content: str, filename: str, caption: str) -> None:
        file_path = Path(tempfile.gettempdir()) / filename
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)
        await self._responder.send_document(file_path, caption=caption)

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in name).strip("_")
