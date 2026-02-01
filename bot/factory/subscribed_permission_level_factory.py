from typing import (
    Awaitable,
    Callable,
    List,
    Optional,
    Type,
)

from aiogram.types import InlineQuery

from bot.factory.permission_level_factory import PermissionLevelFactory
from bot.handlers import (
    AdjustVideoClipHandler,
    BotMessageHandler,
    ClipHandler,
    CompileClipsHandler,
    CompileSelectedClipsHandler,
    DeleteClipHandler,
    EpisodeListHandler,
    InlineClipHandler,
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
            InlineClipHandler,
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

    def get_inline_handler(self) -> Optional[Callable[[InlineQuery], Awaitable[None]]]:
        async def inline_handler(inline_query: InlineQuery):
            query = inline_query.query.strip()
            all_results = []

            handler = InlineClipHandler(message=None, responder=None, logger=self._logger)
            results = await handler.handle_inline(query, self._bot, inline_query.from_user.id)

            if results:
                await inline_query.answer(
                    results=all_results,
                    cache_time=3600,
                    is_personal=True,
                )

        return inline_handler
