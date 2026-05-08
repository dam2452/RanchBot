from typing import (
    Dict,
    List,
    Type,
)

from bot.adapters.rest.rest_middleware_adapter import RestMiddlewareAdapter
from bot.factory.permission_level_factory import PermissionLevelFactory
from bot.handlers import BotMessageHandler


class RestRegistrar:
    def __init__(self, factories: List[PermissionLevelFactory]) -> None:
        self._factories = factories

    def get_command_handlers(self) -> Dict[str, Type[BotMessageHandler]]:
        result: Dict[str, Type[BotMessageHandler]] = {}
        for factory in self._factories:
            for command, handler_cls in factory.get_command_handler_pairs():
                result[command] = handler_cls
        return result

    def get_middleware_adapter(self) -> RestMiddlewareAdapter:
        middlewares = []
        for factory in self._factories:
            middlewares.extend(factory.get_middlewares())
        return RestMiddlewareAdapter(middlewares)
