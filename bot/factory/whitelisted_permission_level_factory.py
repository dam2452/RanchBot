from typing import (
    List,
    Type,
)

from bot.factory.permission_level_factory import PermissionLevelFactory
from bot.handlers import (
    StartHandler,
    SubscriptionStatusHandler,
)
from bot.middlewares import WhitelistMiddleware
from bot.middlewares.bot_middleware import BotMiddleware


class WhitelistedPermissionLevelFactory(PermissionLevelFactory):
    def _create_handler_classes(self) -> List[Type]:
        return [
            StartHandler,
            SubscriptionStatusHandler,
        ]

    def _create_middlewares(self, commands: List[str]) -> List[BotMiddleware]:
        return [WhitelistMiddleware(self._logger, commands)]
