from abc import (
    ABC,
    abstractmethod,
)
import logging
from typing import (
    Awaitable,
    Callable,
    List,
    Tuple,
    Type,
)

from aiogram import (
    Bot,
    Dispatcher,
)
from aiogram.filters import Command
from aiogram.types import Message as AiogramMessage

from bot.adapters.telegram.telegram_message import TelegramMessage
from bot.adapters.telegram.telegram_responder import TelegramResponder
from bot.handlers import BotMessageHandler
from bot.interfaces.message import AbstractMessage
from bot.interfaces.responder import AbstractResponder
from bot.middlewares import BotMiddleware
from bot.middlewares.aiogram_middleware_adapter import AiogramMiddlewareAdapter


class PermissionLevelFactory(ABC):
    def __init__(self, logger: logging.Logger, bot: Bot | None):
        self._logger = logger
        self._bot = bot

    def create_and_register(self, dp: Dispatcher) -> None:
        handler_funcs, middlewares = self.create()

        for command, handler_fn in handler_funcs:
            dp.message.register(handler_fn, Command(commands=[command]))

        self._logger.info(f"{self.__class__.__name__} handlers registered")

        for middleware in middlewares:
            dp.message.middleware.register(AiogramMiddlewareAdapter(middleware))

        self._logger.info(f"{self.__class__.__name__} middlewares registered")

    def create(self) -> Tuple[List[Tuple[str, Callable[[AiogramMessage], Awaitable[None]]]], List[BotMiddleware]]:
        handler_funcs = self.create_handler_funcs()
        commands = [cmd for cmd, _ in handler_funcs]
        middlewares = self.create_middlewares(commands)
        return handler_funcs, middlewares

    def create_handler_funcs(self) -> List[Tuple[str, Callable[[AiogramMessage], Awaitable[None]]]]:
        result = []
        for handler_cls in self.create_handler_classes():
            dummy = handler_cls(message=None, responder=None, logger=self._logger)
            for command in dummy.get_commands():
                result.append((command, self._wrap(handler_cls, self._logger)))
        return result

    @abstractmethod
    def create_handler_classes(self) -> List[Type[BotMessageHandler]]:
        pass

    @abstractmethod
    def create_middlewares(self, commands: List[str]) -> List[BotMiddleware]:
        pass

    @staticmethod
    def _wrap(handler_cls: Type, *args) -> Callable[[AiogramMessage], Awaitable[None]]:
        async def wrapper(msg: AiogramMessage):
            abstract_msg: AbstractMessage = TelegramMessage(msg)
            responder: AbstractResponder = TelegramResponder(msg)
            handler = handler_cls(abstract_msg, responder, *args)
            await handler.handle()
        return wrapper

    def wrap_for_rest_handlers(self) -> List[tuple[str, Type[BotMessageHandler]]]:
        handlers = self.create_handler_classes()
        wrapped = []
        for handler_cls in handlers:
            try:
                dummy = handler_cls(message=None, responder=None, logger=logging.getLogger("dummy"))
            except TypeError:
                continue
            for cmd in dummy.get_commands():
                wrapped.append((cmd, handler_cls))
        return wrapped

    def wrap_for_rest(self, handler_cls: Type, *args) -> Callable[[AbstractMessage, AbstractResponder], Awaitable[None]]:
        async def wrapper(message: AbstractMessage, responder: AbstractResponder):
            handler = handler_cls(message, responder, self._logger, *args)
            await handler.handle()
        return wrapper
