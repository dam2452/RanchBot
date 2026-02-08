import json
from pathlib import Path
import shutil
from typing import (
    List,
    Optional,
)

from aiogram.exceptions import TelegramEntityTooLarge
from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    Message,
)

from bot.exceptions import VideoTooLargeException
from bot.interfaces.responder import AbstractResponder
from bot.settings import settings
from bot.utils.functions import RESOLUTIONS


class TelegramResponder(AbstractResponder):
    def __init__(self, message: Message) -> None:
        self._message = message

    async def send_text(self, text: str) -> Optional[Message]:
        return await self._message.answer(text, reply_to_message_id=self._message.message_id, disable_notification=True)

    async def send_markdown(self, text: str) -> Optional[Message]:
        return await self._message.answer(text, parse_mode="Markdown", reply_to_message_id=self._message.message_id, disable_notification=True)

    async def edit_text(self, message: Message, text: str) -> None:
        try:
            await message.edit_text(text, parse_mode="Markdown")
        except Exception:
            pass

    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: str) -> None:
        await self._message.answer_photo(
            photo=BufferedInputFile(image_bytes, str(image_path)),
            caption=caption,
            show_caption_above_media=True,
            parse_mode="Markdown",
            reply_to_message_id=self._message.message_id,
            disable_notification=True,
        )

    async def send_video(
        self,
        file_path: Path,
        delete_after_send: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
        duration: Optional[float] = None,
        suggestions: Optional[List[str]] = None,
    ) -> None:
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)

            if file_size_mb > settings.FILE_SIZE_LIMIT_MB:
                raise VideoTooLargeException(duration=duration, suggestions=suggestions)

            if width is None or height is None:
                resolution = RESOLUTIONS[settings.DEFAULT_RESOLUTION_KEY]
                width = resolution.width
                height = resolution.height

            await self._message.answer_video(
                video=FSInputFile(file_path),
                width=width,
                height=height,
                supports_streaming=True,
                reply_to_message_id=self._message.message_id,
                disable_notification=True,
            )
        except TelegramEntityTooLarge as exc:
            raise VideoTooLargeException(duration=duration, suggestions=suggestions) from exc
        finally:
            if delete_after_send:
                file_path.unlink()

    async def send_document(self, file_path: Path, caption: str, delete_after_send: bool = True, cleanup_dir: Optional[Path] = None) -> None:
        await self._message.answer_document(
            document=FSInputFile(file_path),
            caption=caption,
            reply_to_message_id=self._message.message_id,
            disable_notification=True,
        )
        if cleanup_dir:
            shutil.rmtree(cleanup_dir, ignore_errors=True)
        elif delete_after_send:
            file_path.unlink()
    async def send_json(self, data: json) -> None:
        raise NotImplementedError("JSON mode not supported for TelegramResponder")
