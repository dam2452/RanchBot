import asyncio
import base64
import logging
from pathlib import Path
from typing import (
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
)

import aiohttp

logger = logging.getLogger(__name__)

_POLL_TIMEOUT = aiohttp.ClientTimeout(total=10)


class SignalHttpClient:
    def __init__(self, base_url: str, phone: str) -> None:
        self.__base_url = base_url.rstrip("/")
        self.__phone = phone
        self.__session: Optional[aiohttp.ClientSession] = None
        self.__receive_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self.__session = aiohttp.ClientSession()

    async def stop(self) -> None:
        if self.__receive_task:
            self.__receive_task.cancel()
            try:
                await self.__receive_task
            except asyncio.CancelledError:
                pass
        if self.__session:
            await self.__session.close()

    def start_receiving(self, handler: Callable[[Dict], Awaitable[None]]) -> None:
        self.__receive_task = asyncio.create_task(self.__receive_loop(handler))

    async def send_text(self, recipient: str, text: str) -> None:
        await self.__post(
            "/v2/send", {
                "message": text,
                "number": self.__phone,
                "recipients": [recipient],
            },
        )

    async def send_file(self, recipient: str, file_path: str, caption: str = "") -> None:
        encoded = base64.b64encode(Path(file_path).read_bytes()).decode()
        await self.__post(
            "/v2/send", {
                "message": caption,
                "number": self.__phone,
                "recipients": [recipient],
                "base64_attachments": [encoded],
            },
        )

    async def __post(self, path: str, body: Dict) -> None:
        if self.__session is None:
            raise RuntimeError("SignalHttpClient has not been started")
        async with self.__session.post(f"{self.__base_url}{path}", json=body) as resp:
            resp.raise_for_status()

    async def __receive_loop(self, handler: Callable[[Dict], Awaitable[None]]) -> None:
        url = f"{self.__base_url}/v1/receive/{self.__phone}"
        logger.info(f"Signal polling started: {url}")

        while True:
            try:
                async with self.__session.get(url, timeout=_POLL_TIMEOUT) as resp:
                    resp.raise_for_status()
                    messages: List[Dict] = await resp.json()

                for msg in messages:
                    asyncio.create_task(handler(msg))

            except Exception as exc:
                logger.warning(f"Signal poll error: {exc}. Retrying in 5s...")
                await asyncio.sleep(5)
