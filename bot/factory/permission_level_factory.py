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
        handler_funcs, middlewares = self.__get_telegram_routes_and_middlewares()

        for command, handler_fn in handler_funcs:
            dp.message.register(handler_fn, Command(commands=[command]))

        self._logger.info(f"{self.__class__.__name__} handlers registered")

        for middleware in middlewares:
            dp.message.middleware.register(AiogramMiddlewareAdapter(middleware))

        self._logger.info(f"{self.__class__.__name__} middlewares registered")

    def __get_telegram_routes_and_middlewares(self) -> Tuple[
        List[Tuple[str, Callable[[AiogramMessage], Awaitable[None]]]],
        List[BotMiddleware],
    ]:
        handler_funcs = self.__get_telegram_handlers()
        commands = [cmd for cmd, _ in handler_funcs]
        middlewares = self._create_middlewares(commands)
        return handler_funcs, middlewares

    def __get_telegram_handlers(self) -> List[Tuple[str, Callable[[AiogramMessage], Awaitable[None]]]]:
        result = []
        for handler_cls in self._create_handler_classes():
            dummy = handler_cls(message=None, responder=None, logger=self._logger)
            for command in dummy.get_commands():
                result.append((command, self.__wrap_telegram_handler(handler_cls, self._logger)))
        return result

    def get_rest_handlers(self) -> List[Tuple[str, Type[BotMessageHandler]]]:
        result = []
        for handler_cls in self._create_handler_classes():
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
    def _create_handler_classes(self) -> List[Type[BotMessageHandler]]:
        pass

    @abstractmethod
    def _create_middlewares(self, commands: List[str]) -> List[BotMiddleware]:
        pass

    def get_inline_handler(self) -> Optional[Callable[[InlineQuery], Awaitable[None]]]:
        return None
