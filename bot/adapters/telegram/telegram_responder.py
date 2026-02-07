import json
from pathlib import Path
import shutil
from typing import Optional

from aiogram.exceptions import TelegramEntityTooLarge
from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    Message,
)

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
    ) -> bool:
        if width is None or height is None:
            resolution = RESOLUTIONS[settings.DEFAULT_RESOLUTION_KEY]
            width = resolution.width
            height = resolution.height

        try:
            await self._message.answer_video(
                video=FSInputFile(file_path),
                width=width,
                height=height,
                supports_streaming=True,
                reply_to_message_id=self._message.message_id,
                disable_notification=True,
            )
            if delete_after_send:
                file_path.unlink()
            return True
        except TelegramEntityTooLarge:
            if delete_after_send:
                file_path.unlink()
            return False

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

    @staticmethod
    def get_file_too_large_message(duration: Optional[float] = None, suggestions: Optional[list[str]] = None) -> str:
        message = "❌ Plik jest za duży do wysłania"
        
        if duration is not None:
            message = f"({duration:.1f}s)"            

        message += ".\n\n Telegram ma limit 50MB dla wideo."

        if suggestions:
            message += "\n\nSpróbuj:\n" + "\n".join(f"• {s}" for s in suggestions)

        return message
