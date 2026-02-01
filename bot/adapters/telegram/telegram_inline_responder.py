import json
from pathlib import Path
from typing import Optional

from aiogram.types import InlineQuery

from bot.interfaces.responder import AbstractResponder


class TelegramInlineResponder(AbstractResponder):
    def __init__(self, message: InlineQuery) -> None:
        self._message = message

    async def send_text(self, text: str) -> None:
        raise NotImplementedError("Inline queries cannot send regular text messages")

    async def send_markdown(self, text: str) -> None:
        raise NotImplementedError("Inline queries cannot send markdown messages")

    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: str) -> None:
        raise NotImplementedError("Inline queries cannot send photos directly")

    async def send_video(
        self,
        file_path: Path,
        delete_after_send: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> None:
        raise NotImplementedError("Inline queries cannot send videos directly")

    async def send_document(self, file_path: Path, caption: str, delete_after_send: bool = True) -> None:
        raise NotImplementedError("Inline queries cannot send documents directly")

    async def send_json(self, data: json) -> None:
        raise NotImplementedError("JSON mode not supported for inline queries")
