import json
from pathlib import Path
import re
import shutil
from typing import (
    List,
    Optional,
)

from bot.adapters.signal.signal_http_client import SignalHttpClient
from bot.interfaces.responder import AbstractResponder


class SignalResponder(AbstractResponder):
    __MD_UNESCAPE = re.compile(r'\\([*_`\[\]()~>#+=|{}.!\-])')
    __MD_FORMAT = re.compile(r'[*_`~]')

    def __init__(self, client: SignalHttpClient, recipient: str) -> None:
        self.__client = client
        self.__recipient = recipient

    @staticmethod
    def __strip_markdown(text: str) -> str:
        text = SignalResponder.__MD_UNESCAPE.sub(r'\1', text)
        return SignalResponder.__MD_FORMAT.sub('', text)

    async def send_text(self, text: str) -> None:
        await self.__client.send_text(self.__recipient, text)

    async def send_markdown(self, text: str) -> None:
        await self.__client.send_text(self.__recipient, self.__strip_markdown(text))

    async def send_photo(self, image_bytes: bytes, image_path: Path, caption: str) -> None:
        image_path.write_bytes(image_bytes)
        try:
            await self.__client.send_file(self.__recipient, str(image_path), self.__strip_markdown(caption))
        finally:
            image_path.unlink(missing_ok=True)

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
            await self.__client.send_file(self.__recipient, str(file_path))
        finally:
            if delete_after_send:
                file_path.unlink(missing_ok=True)

    async def send_document(
        self,
        file_path: Path,
        caption: str,
        delete_after_send: bool = True,
        cleanup_dir: Optional[Path] = None,
    ) -> None:
        try:
            await self.__client.send_file(self.__recipient, str(file_path), self.__strip_markdown(caption))
        finally:
            if cleanup_dir:
                shutil.rmtree(cleanup_dir, ignore_errors=True)
            elif delete_after_send:
                file_path.unlink(missing_ok=True)

    async def send_json(self, data: json) -> None:
        raise NotImplementedError("JSON mode not supported for SignalResponder")
