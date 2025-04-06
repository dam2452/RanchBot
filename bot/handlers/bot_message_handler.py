from abc import (
    ABC,
    abstractmethod,
)
import logging
from pathlib import Path
from typing import (
    Awaitable,
    Callable,
    List,
    Optional,
)

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.interfaces.message import AbstractMessage
from bot.interfaces.responder import AbstractResponder
from bot.responses.bot_message_handler_responses import (
    get_clip_size_exceed_log_message,
    get_clip_size_log_message,
    get_general_error_message,
    get_invalid_args_count_message,
    get_log_clip_duration_exceeded_message,
    get_response,
    get_video_sent_log_message,
)
from bot.settings import settings
from bot.utils.log import (
    log_system_message,
    log_user_activity,
)

ValidatorFunctions = List[Callable[[], Awaitable[bool]]]

class BotMessageHandler(ABC):
    def __init__(self, message: AbstractMessage, responder: AbstractResponder, logger: logging.Logger):
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
        except Exception as e:
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

    async def get_response(self, key: str, args: Optional[List[str]] = None, as_parent: Optional[bool] = False) -> str:
        name = self.get_parent_class_name() if as_parent else self.get_action_name()
        return await get_response(key=key, handler_name=name, args=args)

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
        file_size = file_path.stat().st_size / (1024 * 1024)  # MB
        await self._log_system_message(logging.INFO, get_clip_size_log_message(file_path, file_size))

        if file_size > settings.TELEGRAM_FILE_SIZE_LIMIT_MB:
            await self._log_system_message(logging.WARNING, get_clip_size_exceed_log_message(file_size, settings.TELEGRAM_FILE_SIZE_LIMIT_MB))
            await self._answer(await self.get_response(RK.CLIP_SIZE_EXCEEDED, as_parent=True))
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
            await self._answer_markdown(await self.get_response(RK.LIMIT_EXCEEDED_CLIP_DURATION, as_parent=True))
            await self._log_system_message(logging.INFO, get_log_clip_duration_exceeded_message(self._message.get_user_id()))
            return True
        return False

    async def _validate_argument_count(
            self,
            message: AbstractMessage,
            min_args: int,
            error_message: str,
    ) -> bool:
        content = message.get_text().split()
        if len(content) < min_args:
            await self._reply_invalid_args_count(error_message)
            return False
        return True
