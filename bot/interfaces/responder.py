from abc import (
    ABC,
    abstractmethod,
)
import json
from pathlib import Path


class AbstractResponder(ABC):
    @abstractmethod
    async def send_text(self, text: str) -> None: ...
    @abstractmethod
    async def send_markdown(self, text: str) -> None: ...
    @abstractmethod
    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: str) -> None: ...
    @abstractmethod
    async def send_video(self, file_path: Path, delete_after_send: bool = True) -> None: ...
    @abstractmethod
    async def send_document(self, file_path: Path, caption: str) -> None: ...
    @abstractmethod
    async def send_json(self, data: json) -> None: ...
