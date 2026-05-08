import json
from pathlib import Path
from typing import (
    List,
    Optional,
)

from aiogram.types import InlineQuery

from bot.interfaces.responder import AbstractResponder
from bot.utils.inline_telegram import answer_error


class TelegramInlineResponder(AbstractResponder):
    def __init__(self, inline_query: InlineQuery) -> None:
        self._inline_query = inline_query

    async def send_text(self, text: str) -> None:
        await answer_error(title="Brak dostępu", text=text, inline_query=self._inline_query)

    async def send_markdown(self, text: str) -> None:
        await self.send_text(text)

    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: Optional[str] = None) -> None:
        raise NotImplementedError("send_photo not supported for inline queries")

    async def send_video(
        self,
        file_path: Path,
        delete_after_send: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
        duration: Optional[float] = None,
        suggestions: Optional[List[str]] = None,
    ) -> None:
        raise NotImplementedError("send_video not supported for inline queries")

    async def send_document(self, file_path: Path, caption: str, delete_after_send: bool = True, cleanup_dir: Optional[Path] = None) -> None:
        raise NotImplementedError("send_document not supported for inline queries")

    async def send_json(self, data: json) -> None:
        raise NotImplementedError("send_json not supported for inline queries")
