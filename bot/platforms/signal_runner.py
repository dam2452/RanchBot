import asyncio
import logging
from typing import (
    Awaitable,
    Callable,
    Dict,
    List,
    Type,
)

from bot.adapters.signal.signal_message import SignalMessage
from bot.adapters.signal.signal_responder import SignalResponder
from bot.adapters.signal.signal_rpc import SignalRPC
from bot.database.database_manager import DatabaseManager
from bot.factory import create_all_factories
from bot.handlers import BotMessageHandler
from bot.interfaces.message import AbstractMessage
from bot.interfaces.responder import AbstractResponder
from bot.middlewares import BotMiddleware
from bot.settings import settings

logger = logging.getLogger(__name__)


async def _run_middleware_chain(
    message: AbstractMessage,
    responder: AbstractResponder,
    middlewares: List[BotMiddleware],
    final: Callable[[], Awaitable[None]],
) -> None:
    if not middlewares:
        await final()
        return

    async def next_step() -> None:
        await _run_middleware_chain(message, responder, middlewares[1:], final)

    await middlewares[0].handle(message, responder, next_step)


async def _handle_incoming_event(
    data: Dict,
    rpc: SignalRPC,
    command_handlers: Dict[str, Type[BotMessageHandler]],
    all_middlewares: List[BotMiddleware],
) -> None:
    if data.get("method") != "receive":
        return

    envelope = data.get("params", {}).get("envelope", {})
    data_msg = envelope.get("dataMessage", {})
    text = (data_msg.get("message") or "").strip()
    source = envelope.get("source", "")

    if not source or not text.startswith("/"):
        return

    command = text.split()[0].lstrip("/").lower()
    handler_cls = command_handlers.get(command)

    if handler_cls is None:
        logger.debug(f"Signal: unknown command '/{command}' from {source}")
        return

    user_id = await DatabaseManager.get_or_create_signal_user(source)
    message = SignalMessage(source=source, text=text, user_id=user_id)
    responder = SignalResponder(rpc=rpc, recipient=source)

    async def execute() -> None:
        handler = handler_cls(message, responder, logger)
        await handler.handle()

    await _run_middleware_chain(message, responder, all_middlewares, execute)


async def run_signal_bot() -> None:
    rpc = SignalRPC(
        phone=settings.SIGNAL_PHONE_NUMBER,
        signal_cli_path=settings.SIGNAL_CLI_PATH,
    )

    factories = create_all_factories(logger, bot=None)
    command_handlers: Dict[str, Type[BotMessageHandler]] = {}
    all_middlewares: List[BotMiddleware] = []

    for factory in factories:
        for command, handler_cls in factory.get_rest_handlers():
            command_handlers[command] = handler_cls
        all_middlewares.extend(factory.get_middlewares())

    logger.info(f"Signal: {len(command_handlers)} commands registered, {len(all_middlewares)} middlewares loaded.")

    async def on_event(data: Dict) -> None:
        try:
            await _handle_incoming_event(data, rpc, command_handlers, all_middlewares)
        except Exception as exc:
            logger.exception(f"Signal: error handling event: {exc}")

    rpc.set_event_handler(on_event)
    await rpc.start()
    await rpc.subscribe()

    logger.info(f"Signal bot listening on {settings.SIGNAL_PHONE_NUMBER}.")

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await rpc.stop()
