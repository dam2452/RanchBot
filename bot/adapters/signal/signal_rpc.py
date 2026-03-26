import asyncio
import json
import logging
from typing import (
    Awaitable,
    Callable,
    Dict,
    Optional,
    Set,
)

logger = logging.getLogger(__name__)


class SignalRPC:
    def __init__(self, phone: str, signal_cli_path: str) -> None:
        self.__phone = phone
        self.__signal_cli_path = signal_cli_path
        self.__proc: Optional[asyncio.subprocess.Process] = None  # pylint: disable=no-member
        self.__req_id: int = 0
        self.__pending: Dict[int, asyncio.Future] = {}
        self.__event_tasks: Set[asyncio.Task] = set()
        self.__event_handler: Optional[Callable[[Dict], Awaitable[None]]] = None
        self.__recv_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self.__proc = await asyncio.create_subprocess_exec(
            self.__signal_cli_path,
            "--output", "json",
            "-a", self.__phone,
            "jsonRpc",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info(f"signal-cli started (PID {self.__proc.pid})")
        self.__recv_task = asyncio.create_task(self.__read_loop())

    async def stop(self) -> None:
        if self.__recv_task:
            self.__recv_task.cancel()
            try:
                await self.__recv_task
            except asyncio.CancelledError:
                pass
        for task in self.__event_tasks:
            task.cancel()
        if self.__event_tasks:
            await asyncio.gather(*self.__event_tasks, return_exceptions=True)
        if self.__proc:
            self.__proc.terminate()
            await self.__proc.wait()

    def set_event_handler(self, handler: Callable[[Dict], Awaitable[None]]) -> None:
        self.__event_handler = handler

    async def send_text(self, recipient: str, text: str) -> Dict:
        return await self.__call("send", {"recipient": [recipient], "message": text})

    async def send_file(self, recipient: str, file_path: str, caption: str = "") -> Dict:
        return await self.__call(
            "send", {
                "recipient": [recipient],
                "message": caption,
                "attachments": [file_path],
            },
        )

    async def subscribe(self) -> Dict:
        return await self.__call("subscribeReceive", {})

    async def __call(self, method: str, params: Dict) -> Dict:
        if self.__proc is None:
            raise RuntimeError("SignalRPC has not been started")
        self.__req_id += 1
        req_id = self.__req_id
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }) + "\n"

        fut = asyncio.get_running_loop().create_future()
        self.__pending[req_id] = fut

        self.__proc.stdin.write(payload.encode())
        await self.__proc.stdin.drain()

        try:
            return await asyncio.wait_for(fut, timeout=30)
        except asyncio.TimeoutError:
            self.__pending.pop(req_id, None)
            raise

    async def __read_loop(self) -> None:
        try:
            while True:
                try:
                    line = await self.__proc.stdout.readline()
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
                if req_id is not None and req_id in self.__pending:
                    fut = self.__pending.pop(req_id)
                    if not fut.done():
                        fut.set_result(data)
                elif self.__event_handler is not None:
                    task = asyncio.create_task(self.__event_handler(data))
                    self.__event_tasks.add(task)
                    task.add_done_callback(self.__event_tasks.discard)
        finally:
            for fut in self.__pending.values():
                if not fut.done():
                    fut.set_exception(RuntimeError("signal-cli connection closed"))
            self.__pending.clear()
