from abc import (
    ABC,
    abstractmethod,
)
import json
from pathlib import Path
import tempfile
from typing import (
    List,
    Optional,
)


class AbstractResponder(ABC):
    _MAX_MESSAGE_LENGTH: int = 0

    async def send_text(self, text: str) -> None:
        for part in self._split_message(text):
            await self._send_text_part(part)

    async def send_markdown(self, text: str) -> None:
        for part in self._split_message(text):
            await self._send_markdown_part(part)

    @abstractmethod
    async def _send_text_part(self, text: str) -> None: ...
    @abstractmethod
    async def _send_markdown_part(self, text: str) -> None: ...
    @abstractmethod
    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: Optional[str] = None) -> None: ...
    @abstractmethod
    async def send_video(
        self,
        file_path: Path,
        delete_after_send: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
        duration: Optional[float] = None,
        suggestions: Optional[List[str]] = None,
    ) -> None: ...
    @abstractmethod
    async def send_document(self, file_path: Path, caption: str, delete_after_send: bool = True, cleanup_dir: Optional[Path] = None) -> None: ...
    @abstractmethod
    async def send_json(self, data: json) -> None: ...

    async def send_document_text(self, content: str, filename: str, caption: str) -> None:
        file_path = Path(tempfile.gettempdir()) / filename
        file_path.write_text(content, encoding="utf-8")
        await self.send_document(file_path, caption=caption, delete_after_send=True)

    def _split_message(self, text: str) -> List[str]:
        max_length = self._MAX_MESSAGE_LENGTH
        if max_length <= 0 or len(text) <= max_length:
            return [text]

        code_prefix = ""
        code_suffix = ""
        inner = text

        if text.startswith("```") and text.rstrip().endswith("```"):
            first_newline = text.index("\n") if "\n" in text else len(text)
            code_prefix = text[:first_newline + 1]
            code_suffix = "\n```"
            inner = text[first_newline + 1:]
            if inner.rstrip().endswith("```"):
                inner = inner.rstrip()[:-3]

        parts: List[str] = []
        while len(inner) > max_length:
            split_at = inner.rfind("\n", 0, max_length)
            if split_at == -1:
                split_at = max_length
            parts.append(inner[:split_at])
            inner = inner[split_at:].lstrip("\n")
        parts.append(inner)

        if code_prefix:
            return [code_prefix + p + code_suffix for p in parts]
        return parts
