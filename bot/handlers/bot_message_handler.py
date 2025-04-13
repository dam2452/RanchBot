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

from aiogram import (
    Bot,
    Dispatcher,
)
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    Message,
)

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
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
from bot.utils.resolution import Resolution

ValidatorFunctions = List[Callable[[Message], Awaitable[bool]]]
class BotMessageHandler(ABC):
    def __init__(self, bot: Bot, logger: logging.Logger):
        self._bot: Bot = bot
        self._logger: logging.Logger = logger

    def register(self, dp: Dispatcher) -> None:
        dp.message.register(self.handle, Command(commands=self.get_commands()))

    async def handle(self, message: Message) -> None:
        await self._log_user_activity(message.from_user.id, message.text)

        try:
            for validator in self._get_validator_functions():
                if not await validator(message):
                    return
            await self._do_handle(message)
        except Exception as e:  # pylint: disable=broad-exception-caught
            await self._answer(message,get_general_error_message())
            await self._log_system_message(logging.ERROR, f"{type(e)} Error in {self.get_action_name()} for user '{message.from_user.id}': {e}")

        await DatabaseManager.log_command_usage(message.from_user.id)

    async def _log_system_message(self, level: int, message: str) -> None:
        await log_system_message(level, message, self._logger)

    async def _log_user_activity(self, user_id: int, message: str) -> None:
        await log_user_activity(user_id, message, self._logger)

    async def _reply_invalid_args_count(
        self,
        message: Message,
        response: str,
    ) -> None:
        await self._answer(message,response)
        await self._log_system_message(logging.INFO, get_invalid_args_count_message(self.get_action_name(), message.from_user.id))

    def get_action_name(self) -> str:
        return self.__class__.__name__

    def get_parent_class_name(self) -> str:
        return self.__class__.__bases__[0].__name__

    async def get_response(self, key: str, args: Optional[List[str]] = None, as_parent: Optional[bool] = False) -> str:
        if as_parent:
            return await get_response(key=key, handler_name=self.get_parent_class_name(), args=args)
        return await get_response(key=key, handler_name=self.get_action_name(), args=args)

    @abstractmethod
    def get_commands(self) -> List[str]:
        pass

    @abstractmethod
    async def _do_handle(self, message: Message) -> None:
        pass

    @staticmethod
    async def _answer_markdown(message: Message, text: str) -> None:
        await message.answer(text, parse_mode="Markdown", reply_to_message_id=message.message_id,disable_notification=True)

    @staticmethod
    async def _answer(message: Message, text: str) -> None:
        await message.answer(text, reply_to_message_id=message.message_id,disable_notification=True)

    @staticmethod
    async def _answer_photo(message: Message, image_bytes: bytes, image_path: Path, caption: str) -> None:
        await message.answer_photo(
            photo=BufferedInputFile(image_bytes, str(image_path)),
            caption=caption,
            show_caption_above_media=True,
            parse_mode="Markdown",
            reply_to_message_id=message.message_id,
            disable_notification=True,
        )

    async def _answer_video(self, message: Message, file_path: Path) -> None:
        file_size = file_path.stat().st_size / (1024 * 1024)  # size in MB
        await self._log_system_message(logging.INFO, get_clip_size_log_message(file_path, file_size))

        if file_size > settings.TELEGRAM_FILE_SIZE_LIMIT_MB:
            await self._log_system_message(
                logging.WARNING,
                get_clip_size_exceed_log_message(file_size, settings.TELEGRAM_FILE_SIZE_LIMIT_MB),
            )
            await self._answer(message, await self.get_response(RK.CLIP_SIZE_EXCEEDED, as_parent=True))
        else:
            resolution = Resolution.from_str(settings.DEFAULT_RESOLUTION_KEY)

            await message.answer_video(
                FSInputFile(file_path),
                supports_streaming=True,
                width=resolution.width,
                height=resolution.height,
                reply_to_message_id=message.message_id,
                disable_notification = True,
            )
            await self._log_system_message(logging.INFO, get_video_sent_log_message(file_path))

    async def _answer_document(self, message: Message, file_path: Path, caption: str) -> None:
        await message.answer_document(
            FSInputFile(file_path),
            caption=caption,
            reply_to_message_id=message.message_id,
            disable_notification=True,
        )
        await self._log_system_message(logging.INFO, get_video_sent_log_message(file_path))
    @abstractmethod
    def _get_validator_functions(self) -> ValidatorFunctions:
        return []
    async def _handle_clip_duration_limit_exceeded(self, message: Message, clip_duration: float) -> bool:
        if not await DatabaseManager.is_admin_or_moderator(message.from_user.id) and clip_duration > settings.MAX_CLIP_DURATION:
            await self._answer_markdown(message, await self.get_response(RK.LIMIT_EXCEEDED_CLIP_DURATION, as_parent=True))
            await self._log_system_message(logging.INFO, get_log_clip_duration_exceeded_message(message.from_user.id))
            return True

        return False

    async def _validate_argument_count(self, message: Message, min_args: int, error_message: str) -> bool:
        content = message.text.split()
        if len(content) < min_args:
            await self._reply_invalid_args_count(message, error_message)
            await self._log_system_message(logging.INFO, get_invalid_args_count_message(self.get_action_name(),message.from_user.id))
            return False
        return True
