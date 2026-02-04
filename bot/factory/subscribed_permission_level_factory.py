import asyncio
import logging
from typing import (
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Type,
)

from aiogram import Bot
from aiogram.types import InlineQuery

from bot.adapters.telegram.telegram_inline_query import TelegramInlineQuery
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
    SerialContextHandler,
)
from bot.middlewares import (
    BotMiddleware,
    SubscriberMiddleware,
)
from bot.responses.bot_message_handler_responses import get_general_error_message
from bot.utils.inline_telegram import answer_error
from bot.utils.log import log_system_message


class SubscribedPermissionLevelFactory(PermissionLevelFactory):
    def __init__(self, logger: logging.Logger, bot: Optional[Bot]):
        super().__init__(logger, bot)
        self._inline_user_sessions: Dict[int, asyncio.Task] = {}

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
            SerialContextHandler,
        ]

    def create_middlewares(self, commands: List[str]) -> List[BotMiddleware]:
        return [
            SubscriberMiddleware(self._logger, commands),
        ]

    def get_inline_handler(self) -> Optional[Callable[[InlineQuery], Awaitable[None]]]:
        async def process_inline_query(inline_query: InlineQuery):
            user_id = inline_query.from_user.id
            try:
                if not inline_query.query:
                    return

                if not await DatabaseManager.is_user_subscribed(user_id):
                    await log_system_message(logging.WARNING, f"Unauthorized inline query from user {user_id}", self._logger)
                    await answer_error(
                        title="❌ Brak uprawnień",
                        text="❌ Brak uprawnień do używania inline mode",
                        inline_query=inline_query,
                    )
                    return

                handler = InlineClipHandler(message=TelegramInlineQuery(inline_query), responder=None, logger=self._logger)
                results = await handler.handle_inline(self._bot)

                await inline_query.answer(
                    results=results,
                    cache_time=300,
                    is_personal=True,
                )
            except asyncio.CancelledError:
                await log_system_message(logging.INFO, f"Inline query cancelled for user {user_id} (replaced by newer query)", self._logger)
                raise
            except Exception as e:
                await log_system_message(logging.ERROR, f"Failed to handle inline query: {e}", self._logger)
                try:
                    await answer_error(
                        title="❌ Wystąpił błąd",
                        text=get_general_error_message(),
                        inline_query=inline_query,
                    )
                except Exception as exc:
                    await log_system_message(logging.ERROR, f"Failed to report inline error: {exc}", self._logger)

        async def inline_handler(inline_query: InlineQuery):
            user_id = inline_query.from_user.id

            if user_id in self._inline_user_sessions:
                old_task = self._inline_user_sessions[user_id]
                old_task.cancel()
                await log_system_message(logging.INFO, f"Cancelling previous inline query for user {user_id}", self._logger)

            task = asyncio.create_task(process_inline_query(inline_query))
            self._inline_user_sessions[user_id] = task

            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                if self._inline_user_sessions.get(user_id) == task:
                    del self._inline_user_sessions[user_id]

        return inline_handler
