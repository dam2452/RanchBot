from typing import (
    List,
    Type,
)

from bot.factory.permission_level_factory import PermissionLevelFactory
from bot.handlers import (
    AdminHelpHandler,
    ListAdminsHandler,
    ListModeratorsHandler,
    ListWhitelistHandler,
    TranscriptionHandler,
    UpdateUserNoteHandler,
)
from bot.middlewares import ModeratorMiddleware
from bot.middlewares.bot_middleware import BotMiddleware


class ModeratorPermissionLevelFactory(PermissionLevelFactory):
    def _create_handler_classes(self) -> List[Type]:
        return [
            AdminHelpHandler,
            ListAdminsHandler,
            ListModeratorsHandler,
            ListWhitelistHandler,
            TranscriptionHandler,
            UpdateUserNoteHandler,
        ]

    def _create_middlewares(self, commands: List[str]) -> List[BotMiddleware]:
        return [ModeratorMiddleware(self._logger, commands)]
