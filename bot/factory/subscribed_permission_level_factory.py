from typing import (
    Awaitable,
    Callable,
    List,
    Optional,
    Type,
)
from uuid import uuid4

from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from bot.database.database_manager import DatabaseManager
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
            try:
                user_id = inline_query.from_user.id

                if not await DatabaseManager.is_user_subscribed(user_id):
                    self._logger.warning(f"Unauthorized inline query from user {user_id}")
                    unauthorized_result = InlineQueryResultArticle(
                        id=str(uuid4()),
                        title="❌ Brak uprawnień",
                        description="Musisz być subskrybentem, moderatorem lub adminem, aby używać inline mode",
                        input_message_content=InputTextMessageContent(
                            message_text="❌ Brak uprawnień do używania inline mode",
                        ),
                    )
                    await inline_query.answer(
                        results=[unauthorized_result],
                        cache_time=0,
                        is_personal=True,
                    )
                    return

                query = inline_query.query.strip()

                handler = InlineClipHandler(message=None, responder=None, logger=self._logger)
                results = await handler.handle_inline(query, self._bot, user_id)

                await inline_query.answer(
                    results=results,
                    cache_time=3600,
                    is_personal=True,
                )

            except Exception as e:
                self._logger.error(f"Critical error in inline handler: {type(e).__name__}: {e}")
                try:
                    error_result = InlineQueryResultArticle(
                        id=str(uuid4()),
                        title="Wystąpił błąd",
                        description="Spróbuj ponownie później",
                        input_message_content=InputTextMessageContent(
                            message_text="❌ Wystąpił nieoczekiwany błąd",
                        ),
                    )
                    await inline_query.answer(
                        results=[error_result],
                        cache_time=0,
                        is_personal=True,
                    )
                except Exception as answer_error:
                    self._logger.error(f"Failed to send error response: {answer_error}")

        return inline_handler
