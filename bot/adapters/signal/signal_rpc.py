import asyncio
import json
import logging
from typing import (
    Awaitable,
    Callable,
    Dict,
    Optional,
)

logger = logging.getLogger(__name__)


class SignalRPC:
    def __init__(self, phone: str, signal_cli_path: str) -> None:
        self._phone = phone
        self._signal_cli_path = signal_cli_path
        self._proc: Optional[asyncio.subprocess.Process] = None  # pylint: disable=no-member
        self._req_id: int = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._event_handler: Optional[Callable[[Dict], Awaitable[None]]] = None
        self._recv_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            self._signal_cli_path,
            "--output", "json",
            "-a", self._phone,
            "jsonRpc",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info(f"signal-cli started (PID {self._proc.pid})")
        self._recv_task = asyncio.create_task(self._read_loop())

    async def stop(self) -> None:
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        if self._proc:
            self._proc.terminate()
            await self._proc.wait()

    def set_event_handler(self, handler: Callable[[Dict], Awaitable[None]]) -> None:
        self._event_handler = handler

    async def send_text(self, recipient: str, text: str) -> Dict:
        return await self._call("send", {"recipient": [recipient], "message": text})

    async def send_file(self, recipient: str, file_path: str, caption: str = "") -> Dict:
        return await self._call(
            "send", {
                "recipient": [recipient],
                "message": caption,
                "attachments": [file_path],
            },
        )

    async def subscribe(self) -> Dict:
        return await self._call("subscribeReceive", {})

    async def _call(self, method: str, params: Dict) -> Dict:
        self._req_id += 1
        req_id = self._req_id
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }) + "\n"

        loop = asyncio.get_event_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[req_id] = fut

        self._proc.stdin.write(payload.encode())
        await self._proc.stdin.drain()

        return await asyncio.wait_for(fut, timeout=30)

    async def _read_loop(self) -> None:
        while True:
            try:
                line = await self._proc.stdout.readline()
            except Exception as exc:
                logger.error(f"signal-cli stdout read error: {exc}")
                break

            if not line:
                logger.warning("signal-cli closed stdout.")
                break

            text = line.decode().strip()
            if not text:
                continue

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                logger.debug(f"Non-JSON line from signal-cli: {text}")
                continue

            req_id = data.get("id")
            if req_id is not None and req_id in self._pending:
                fut = self._pending.pop(req_id)
                if not fut.done():
                    fut.set_result(data)
            elif self._event_handler is not None:
                asyncio.create_task(self._event_handler(data))
