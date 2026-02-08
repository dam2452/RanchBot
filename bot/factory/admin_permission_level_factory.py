from typing import (
    List,
    Type,
)

from bot.factory.permission_level_factory import PermissionLevelFactory
from bot.handlers import (
    AddSubscriptionHandler,
    AddWhitelistHandler,
    CreateKeyHandler,
    ListKeysHandler,
    ReindexHandler,
    RemoveKeyHandler,
    RemoveSubscriptionHandler,
    RemoveWhitelistHandler,
)
from bot.middlewares import AdminMiddleware
from bot.middlewares.bot_middleware import BotMiddleware


class AdminPermissionLevelFactory(PermissionLevelFactory):
    def _create_handler_classes(self) -> List[Type]:
        return [
            AddSubscriptionHandler,
            AddWhitelistHandler,
            RemoveSubscriptionHandler,
            RemoveWhitelistHandler,
            CreateKeyHandler,
            RemoveKeyHandler,
            ListKeysHandler,
            ReindexHandler,
        ]

    def _create_middlewares(self, commands: List[str]) -> List[BotMiddleware]:
        return [AdminMiddleware(self._logger, commands)]
