import asyncio
import logging
from typing import (
    Awaitable,
    Callable,
    List,
)

from aiogram import (
    Bot,
    Dispatcher,
)
from aiogram.filters import Command
from aiogram.types import (
    InlineQuery,
    Message as AiogramMessage,
)

from bot.adapters.telegram.protocols import SupportsInlineQuery
from bot.adapters.telegram.telegram_message import TelegramMessage
from bot.adapters.telegram.telegram_responder import TelegramResponder
from bot.factory.permission_level_factory import PermissionLevelFactory
from bot.handlers import BotMessageHandler
from bot.interfaces.message import AbstractMessage
from bot.interfaces.responder import AbstractResponder
from bot.middlewares.aiogram_middleware_adapter import AiogramMiddlewareAdapter

logger = logging.getLogger(__name__)

_active_inline_tasks: dict = {}


class TelegramRegistrar:
    def __init__(self, factories: List[PermissionLevelFactory], dp: Dispatcher, bot: Bot) -> None:
        self._factories = factories
        self._dp = dp
        self._bot = bot

    def register(self) -> None:
        self._register_command_handlers()
        self._register_inline_handlers()
        logger.info("All Telegram handlers and middlewares registered.")

    def _register_command_handlers(self) -> None:
        for factory in self._factories:
            for command, handler_cls in factory.get_command_handler_pairs():
                self._dp.message.register(
                    self._wrap_handler(handler_cls, factory._logger),
                    Command(commands=[command]),
                )
            for middleware in factory.get_middlewares():
                self._dp.message.middleware.register(AiogramMiddlewareAdapter(middleware))
            logger.info(f"{factory.__class__.__name__} registered")

    def _register_inline_handlers(self) -> None:
        inline_factories = [f for f in self._factories if isinstance(f, SupportsInlineQuery)]

        for factory in inline_factories:
            for middleware in factory.get_middlewares():
                self._dp.inline_query.middleware.register(AiogramMiddlewareAdapter(middleware))

        inline_handlers: List[Callable[[InlineQuery], Awaitable[None]]] = [
            factory.get_inline_handler(self._bot)
            for factory in inline_factories
        ]

        if not inline_handlers:
            return

        async def combined_inline_handler(inline_query: InlineQuery) -> None:
            user_id = inline_query.from_user.id

            existing = _active_inline_tasks.get(user_id)
            if existing and not existing.done():
                existing.cancel()
                try:
                    await existing
                except asyncio.CancelledError:
                    pass

            async def _process() -> None:
                try:
                    for handler in inline_handlers:
                        await handler(inline_query)
                        break
                except asyncio.CancelledError:
                    logger.info(f"Cancelled previous inline session for user {user_id}")
                except Exception as e:
                    logger.error(f"Error in inline handler: {type(e).__name__}: {e}", exc_info=True)
                finally:
                    _active_inline_tasks.pop(user_id, None)

            task = asyncio.create_task(_process())
            _active_inline_tasks[user_id] = task
            await task

        self._dp.inline_query.register(combined_inline_handler)
        logger.info("Combined inline handler registered")

    @staticmethod
    def _wrap_handler(handler_cls: type, handler_logger: logging.Logger) -> Callable[[AiogramMessage], Awaitable[None]]:
        async def wrapper(msg: AiogramMessage) -> None:
            abstract_msg: AbstractMessage = TelegramMessage(msg)
            responder: AbstractResponder = TelegramResponder(msg)
            handler: BotMessageHandler = handler_cls(abstract_msg, responder, handler_logger)
            await handler.handle()
        return wrapper
