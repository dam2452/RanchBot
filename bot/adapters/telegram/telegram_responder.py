import json
from pathlib import Path

from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    Message,
)

from bot.interfaces.responder import AbstractResponder


class TelegramResponder(AbstractResponder):
    def __init__(self, message: Message) -> None:
        self._message = message

    async def send_text(self, text: str) -> None:
        await self._message.answer(text, reply_to_message_id=self._message.message_id, disable_notification=True)

    async def send_markdown(self, text: str) -> None:
        await self._message.answer(text, parse_mode="Markdown", reply_to_message_id=self._message.message_id, disable_notification=True)

    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: str) -> None:
        await self._message.answer_photo(
            photo=BufferedInputFile(image_bytes, str(image_path)),
            caption=caption,
            show_caption_above_media=True,
            parse_mode="Markdown",
            reply_to_message_id=self._message.message_id,
            disable_notification=True,
        )

    async def send_video(self, file_path: Path, delete_after_send: bool = True) -> None:
        await self._message.answer_video(
            video=FSInputFile(file_path),
            supports_streaming=True,
            reply_to_message_id=self._message.message_id,
            disable_notification=True,
        )
        if delete_after_send:
            file_path.unlink()

    async def send_document(self, file_path: Path, caption: str) -> None:
        await self._message.answer_document(
            document=FSInputFile(file_path),
            caption=caption,
            reply_to_message_id=self._message.message_id,
            disable_notification=True,
        )
    async def send_json(self, data: json) -> None:
        raise NotImplementedError("JSON mode not supported for TelegramResponder")
