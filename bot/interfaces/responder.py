from abc import (
    ABC,
    abstractmethod,
)
from pathlib import Path


class AbstractResponder(ABC):
    @abstractmethod
    async def send_text(self, text: str): ...
    @abstractmethod
    async def send_markdown(self, text: str): ...
    @abstractmethod
    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: str): ...
    @abstractmethod
    async def send_video(self, file_path: Path): ...
    @abstractmethod
    async def send_document(self, file_path: Path, caption: str): ...
