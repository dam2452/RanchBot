import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import (
    Awaitable,
    Callable,
    Dict,
    Optional,
)

import aiohttp

logger = logging.getLogger(__name__)


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
        ws_url = self.__base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/v1/receive/{self.__phone}"

        while True:
            try:
                async with self.__session.ws_connect(ws_url) as ws:
                    logger.info("Signal WebSocket connected.")
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                            except json.JSONDecodeError:
                                logger.debug(f"Signal WS non-JSON: {msg.data}")
                                continue
                            asyncio.create_task(handler(data))
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"Signal WS error: {ws.exception()}")
                            break
            except Exception as exc:
                logger.warning(f"Signal WS disconnected: {exc}. Reconnecting in 5s...")
                await asyncio.sleep(5)
