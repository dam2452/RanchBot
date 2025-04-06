from typing import (
    List,
    Type,
)

from bot.factory.permission_level_factory import PermissionLevelFactory
from bot.handlers import (
    AdjustVideoClipHandler,
    BotMessageHandler,
    ClipHandler,
    CompileClipsHandler,
    CompileSelectedClipsHandler,
    DeleteClipHandler,
    EpisodeListHandler,
    ManualClipHandler,
    MyClipsHandler,
    ReportIssueHandler,
    SaveClipHandler,
    SearchHandler,
    SearchListHandler,
    SelectClipHandler,
    SendClipHandler,
)
from bot.middlewares import (
    BotMiddleware,
    SubscriberMiddleware,
)


class SubscribedPermissionLevelFactory(PermissionLevelFactory):
    def create_handler_classes(self) -> List[Type[BotMessageHandler]]:
        return [
            AdjustVideoClipHandler,
            ClipHandler,
            CompileClipsHandler,
            CompileSelectedClipsHandler,
            DeleteClipHandler,
            EpisodeListHandler,
            ManualClipHandler,
            MyClipsHandler,
            ReportIssueHandler,
            SaveClipHandler,
            SearchHandler,
            SearchListHandler,
            SelectClipHandler,
            SendClipHandler,
        ]

    def create_middlewares(self, commands: List[str]) -> List[BotMiddleware]:
        return [
            SubscriberMiddleware(self._logger, commands),
        ]
