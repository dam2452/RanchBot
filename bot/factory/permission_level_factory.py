from abc import (
    ABC,
    abstractmethod,
)
from functools import cached_property
import logging
from typing import (
    Dict,
    List,
    Tuple,
    Type,
)

from bot.handlers import BotMessageHandler
from bot.middlewares import BotMiddleware


class PermissionLevelFactory(ABC):
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    @cached_property
    def _handler_classes(self) -> List[Type[BotMessageHandler]]:
        classes = self._create_handler_classes()
        self._assert_no_command_collisions(classes)
        return classes

    def get_command_handler_pairs(self) -> List[Tuple[str, Type[BotMessageHandler]]]:
        return [
            (command, handler_cls)
            for handler_cls in self._handler_classes
            for command in handler_cls.get_commands()
        ]

    def get_middlewares(self) -> List[BotMiddleware]:
        commands = [cmd for cmd, _ in self.get_command_handler_pairs()]
        return self._create_middlewares(commands)

    @staticmethod
    def _assert_no_command_collisions(classes: List[Type[BotMessageHandler]]) -> None:
        seen: Dict[str, Type[BotMessageHandler]] = {}
        for handler_cls in classes:
            for command in handler_cls.get_commands():
                if command in seen:
                    raise ValueError(
                        f"Command collision: '/{command}' registered by both "
                        f"{seen[command].__name__} and {handler_cls.__name__}",
                    )
                seen[command] = handler_cls

    @abstractmethod
    def _create_handler_classes(self) -> List[Type[BotMessageHandler]]:
        pass

    @abstractmethod
    def _create_middlewares(self, commands: List[str]) -> List[BotMiddleware]:
        pass
