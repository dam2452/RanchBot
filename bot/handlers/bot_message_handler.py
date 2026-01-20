from abc import (
    ABC,
    abstractmethod,
)
import logging
from pathlib import Path
import re
from typing import (
    Awaitable,
    Callable,
    List,
    Optional,
)

from bot.adapters.rest.models import ResponseStatus as RS
from bot.database.database_manager import DatabaseManager
from bot.interfaces.message import AbstractMessage
from bot.interfaces.responder import AbstractResponder
from bot.responses.bot_message_handler_responses import (
    get_clip_size_exceed_log_message,
    get_clip_size_exceed_message,
    get_clip_size_log_message,
    get_general_error_message,
    get_invalid_args_count_message,
    get_log_clip_duration_exceeded_message,
    get_video_sent_log_message,
)
from bot.responses.sending_videos.manual_clip_handler_responses import get_limit_exceeded_clip_duration_message
from bot.settings import settings
from bot.utils.log import (
    log_system_message,
    log_user_activity,
)

ValidatorFunctions = List[Callable[[], Awaitable[bool]]]

class BotMessageHandler(ABC):
    def __init__(self, message: Optional[AbstractMessage], responder: Optional[AbstractResponder], logger: logging.Logger):
        self._message = message
        self._responder = responder
        self._logger = logger

    async def handle(self) -> None:
        await self._log_user_activity(self._message.get_user_id(), self._message.get_text())

        try:
            validators = await self._get_validator_functions()
            for validator in validators:
                if not await validator():
                    return

            await self._do_handle()
        except Exception as e: # pylint: disable=broad-exception-caught
            await self._responder.send_text(get_general_error_message())
            await self._log_system_message(
                logging.ERROR,
                f"{type(e)} Error in {self.get_action_name()} for user '{self._message.get_user_id()}': {e}",
            )

        await DatabaseManager.log_command_usage(self._message.get_user_id())

    async def _log_system_message(self, level: int, message: str) -> None:
        await log_system_message(level, message, self._logger)

    async def _log_user_activity(self, user_id: int, message: str) -> None:
        await log_user_activity(user_id, message, self._logger)

    async def _reply_invalid_args_count(self, response: str) -> None:
        await self._responder.send_text(response)
        await self._log_system_message(logging.INFO, get_invalid_args_count_message(self.get_action_name(), self._message.get_user_id()))

    def get_action_name(self) -> str:
        return self.__class__.__name__

    def get_parent_class_name(self) -> str:
        return self.__class__.__bases__[0].__name__

    @abstractmethod
    def get_commands(self) -> List[str]:
        pass

    @abstractmethod
    async def _do_handle(self) -> None:
        pass

    async def _answer_markdown(self, text: str) -> None:
        await self._responder.send_markdown(text)

    async def _answer(self, text: str) -> None:
        await self._responder.send_text(text)

    async def _answer_photo(self, image_bytes: bytes, image_path: Path, caption: str) -> None:
        await self._responder.send_photo(image_bytes, image_path, caption)

    async def _answer_video(self, file_path: Path) -> None:
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        await self._log_system_message(logging.INFO, get_clip_size_log_message(file_path, file_size_mb))

        if file_size_mb > settings.FILE_SIZE_LIMIT_MB:
            await self._log_system_message(logging.WARNING, get_clip_size_exceed_log_message(file_size_mb, settings.FILE_SIZE_LIMIT_MB))
            await self._answer(get_clip_size_exceed_message())
        else:
            await self._responder.send_video(file_path)
            await self._log_system_message(logging.INFO, get_video_sent_log_message(file_path))

    async def _answer_document(self, file_path: Path, caption: str) -> None:
        await self._responder.send_document(file_path, caption)
        await self._log_system_message(logging.INFO, get_video_sent_log_message(file_path))

    @abstractmethod
    async def _get_validator_functions(self) -> ValidatorFunctions:
        pass

    async def _handle_clip_duration_limit_exceeded(self, clip_duration: float) -> bool:
        if not await DatabaseManager.is_admin_or_moderator(self._message.get_user_id()) and clip_duration > settings.MAX_CLIP_DURATION:
            await self._answer_markdown(get_limit_exceeded_clip_duration_message())
            await self._log_system_message(logging.INFO, get_log_clip_duration_exceeded_message(self._message.get_user_id()))
            return True
        return False

    async def _validate_argument_count(
            self,
            message: AbstractMessage,
            min_args: float,
            error_message: str,
            max_args: Optional[float] = None,
    ) -> bool:
        if max_args is None:
            max_args = min_args

        if min_args <= (len(message.get_text().split()) - 1) <= max_args:
            return True

        await self._reply_invalid_args_count(error_message)
        return False

    async def reply(
            self,
            message: str,
            data: Optional[dict] = None,
            status: RS = RS.SUCCESS,
    ) -> None:
        if self._message.should_reply_json():
            response_data = {
                "status": status,
                "message": message,
            }
            if data:
                response_data["data"] = data
            await self._responder.send_json(response_data)
        else:
            await self._responder.send_markdown(await self.escape_markdown(message))

    async def reply_error(self, message: str, data: Optional[dict] = None):
        await self.reply(message, data, RS.ERROR)

    @staticmethod
    async def escape_markdown(text: str) -> str:
        return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)
