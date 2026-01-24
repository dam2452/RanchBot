from abc import (
    ABC,
    abstractmethod,
)
import logging
from typing import (
    Awaitable,
    Callable,
    List,
    Optional,
    Tuple,
    Type,
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

from bot.adapters.telegram.telegram_message import TelegramMessage
from bot.adapters.telegram.telegram_responder import TelegramResponder
from bot.handlers import BotMessageHandler
from bot.interfaces.message import AbstractMessage
from bot.interfaces.responder import AbstractResponder
from bot.middlewares import BotMiddleware
from bot.middlewares.aiogram_middleware_adapter import AiogramMiddlewareAdapter


class PermissionLevelFactory(ABC):
    def __init__(self, logger: logging.Logger, bot: Optional[Bot]):
        self._logger = logger
        self._bot = bot

    def create_and_register(self, dp: Dispatcher) -> None:
        handler_funcs, middlewares = self.get_telegram_routes_and_middlewares()

        for command, handler_fn in handler_funcs:
            dp.message.register(handler_fn, Command(commands=[command]))

        self._logger.info(f"{self.__class__.__name__} handlers registered")

        for middleware in middlewares:
            dp.message.middleware.register(AiogramMiddlewareAdapter(middleware))

        self._logger.info(f"{self.__class__.__name__} middlewares registered")

    def get_telegram_routes_and_middlewares(self) -> Tuple[
        List[Tuple[str, Callable[[AiogramMessage], Awaitable[None]]]],
        List[BotMiddleware],
    ]:
        handler_funcs = self.get_telegram_handlers()
        commands = [cmd for cmd, _ in handler_funcs]
        middlewares = self.create_middlewares(commands)
        return handler_funcs, middlewares

    def get_telegram_handlers(self) -> List[Tuple[str, Callable[[AiogramMessage], Awaitable[None]]]]:
        result = []
        for handler_cls in self.create_handler_classes():
            dummy = handler_cls(message=None, responder=None, logger=self._logger)
            for command in dummy.get_commands():
                result.append((command, self.__wrap_telegram_handler(handler_cls, self._logger)))
        return result

    def get_rest_handlers(self) -> List[Tuple[str, Type[BotMessageHandler]]]:
        result = []
        for handler_cls in self.create_handler_classes():
            dummy = handler_cls(message=None, responder=None, logger=self._logger)
            for command in dummy.get_commands():
                result.append((command, handler_cls))
        return result

    @staticmethod
    def __wrap_telegram_handler(
        handler_cls: Type[BotMessageHandler],
        logger: logging.Logger,
    ) -> Callable[[AiogramMessage], Awaitable[None]]:
        async def wrapper(msg: AiogramMessage):
            abstract_msg: AbstractMessage = TelegramMessage(msg)
            responder: AbstractResponder = TelegramResponder(msg)
            handler = handler_cls(abstract_msg, responder, logger)
            await handler.handle()
        return wrapper

    @abstractmethod
    def create_handler_classes(self) -> List[Type[BotMessageHandler]]:
        pass

    @abstractmethod
    def create_middlewares(self, commands: List[str]) -> List[BotMiddleware]:
        pass

    def get_inline_handler(self) -> Optional[Callable[[InlineQuery], Awaitable[None]]]:
        handlers_with_inline = [
            handler_cls
            for handler_cls in self.create_handler_classes()
            if handler_cls(message=None, responder=None, logger=self._logger).supports_inline_mode()
        ]

        if not handlers_with_inline:
            return None

        async def inline_handler(inline_query: InlineQuery):
            query = inline_query.query.strip()
            all_results = []

            for handler_cls in handlers_with_inline:
                handler = handler_cls(message=None, responder=None, logger=self._logger)
                results = await handler.handle_inline_query(query)
                if results:
                    all_results.extend(results)

            await inline_query.answer(
                results=all_results,
                cache_time=1,
                is_personal=True,
            )

            self._logger.info(f"Inline query handled for user {inline_query.from_user.id}: '{query}'")

        return inline_handler
