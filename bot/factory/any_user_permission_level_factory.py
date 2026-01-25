from typing import (
    List,
    Type,
)

from bot.factory.permission_level_factory import PermissionLevelFactory
from bot.handlers import SaveUserKeyHandler
from bot.middlewares import AnyMiddleware
from bot.middlewares.bot_middleware import BotMiddleware


class AnyUserPermissionLevelFactory(PermissionLevelFactory):
    def create_handler_classes(self) -> List[Type]:
        return [SaveUserKeyHandler]

    def create_middlewares(self, commands: List[str]) -> List[BotMiddleware]:
        return [AnyMiddleware(self._logger, commands)]
