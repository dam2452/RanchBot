from abc import (
    ABC,
    abstractmethod,
)
import json
from pathlib import Path
from typing import Optional


class AbstractResponder(ABC):
    @abstractmethod
    async def send_text(self, text: str) -> None: ...
    @abstractmethod
    async def send_markdown(self, text: str) -> None: ...
    @abstractmethod
    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: str) -> None: ...
    @abstractmethod
    async def send_video(
        self,
        file_path: Path,
        delete_after_send: bool = True,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> bool: ...
    @abstractmethod
    async def send_document(self, file_path: Path, caption: str, delete_after_send: bool = True, cleanup_dir: Optional[Path] = None) -> None: ...
    @abstractmethod
    async def send_json(self, data: json) -> None: ...
