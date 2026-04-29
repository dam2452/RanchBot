from abc import abstractmethod
import logging
import math
from typing import (
    Any,
    List,
    Optional,
    cast,
)

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import get_message_too_long_message
from bot.responses.filter_command_messages import (
    get_no_filter_set_message,
    get_no_segments_match_active_filter_message,
)
from bot.services.search_filter.active_filter_scene_segments import (
    ActiveFilterSceneSegmentsStatus,
    load_active_filter_scene_segments,
)
from bot.services.search_filter.active_filter_text_segments import (
    ActiveFilterTextSegmentsOutcome,
    ActiveFilterTextSegmentsStatus,
    load_active_filter_text_segments,
)
from bot.settings import settings
from bot.types import SearchFilter


class ActiveFilterTextCommandHandler(BotMessageHandler):
    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__validate_arg_count,
            self.__validate_length_when_quote,
        ]

    async def __validate_arg_count(self) -> bool:
        return await self._validate_argument_count(self._message, 0, math.inf)

    async def __validate_length_when_quote(self) -> bool:
        msg = self._message
        assert msg is not None
        parts = msg.get_text().split()
        if len(parts) <= 1:
            return True
        if not await DatabaseManager.is_admin_or_moderator(msg.get_user_id()) and len(
                msg.get_text(),
        ) > settings.MAX_SEARCH_QUERY_LENGTH:
            await self._reply_error(get_message_too_long_message())
            return False
        return True

    def _get_usage_message(self) -> str:
        return get_no_filter_set_message()

    @abstractmethod
    def _active_filter_es_query_size(self) -> int:
        pass

    @abstractmethod
    def _log_no_filter_results_message(self, chat_id: int) -> str:
        pass

    @abstractmethod
    async def _handle_active_filter_segments_ok(
            self,
            *,
            chat_id: int,
            series_name: str,
            outcome: ActiveFilterTextSegmentsOutcome,
    ) -> None:
        pass

    async def _search_with_active_filter(
            self,
            *,
            quote: str,
            chat_id: int,
            series_name: str,
            default_es_size: int,
            error_message: str,
    ):
        search_filter: Optional[SearchFilter] = await DatabaseManager.get_user_filters(chat_id)
        es_size = default_es_size
        if search_filter and (
            search_filter.get("character_groups")
            or search_filter.get("emotions")
            or search_filter.get("object_groups")
        ):
            es_size = 1000

        return await self._find_and_filter_segments(
            quote=quote,
            series_name=series_name,
            search_filter=search_filter,
            es_size=es_size,
            error_message=error_message,
        )

    @abstractmethod
    async def _handle_with_quote(
            self,
            quote: str,
            chat_id: int,
            series_name: str,
            msg: Any,
    ) -> None:
        pass

    async def _do_handle(self) -> None:
        msg = self._message
        assert msg is not None
        chat_id = msg.get_chat_id()
        series_name = await self._get_user_active_series(msg.get_user_id())

        content = self._get_message_content()
        if len(content) > 1:
            quote = self._get_quote()
            await self._handle_with_quote(quote, chat_id, series_name, msg)
            return

        outcome = await load_active_filter_text_segments(
            chat_id=chat_id,
            series_name=series_name,
            logger=self._logger,
            es_query_size=self._active_filter_es_query_size(),
        )

        if outcome.status == ActiveFilterTextSegmentsStatus.NO_FILTER:
            await self._reply_error(get_no_filter_set_message())
            return

        if outcome.status in (
                ActiveFilterTextSegmentsStatus.NO_CANDIDATES,
                ActiveFilterTextSegmentsStatus.NO_MATCHES_POST_FILTER,
        ):
            await self._reply_error(get_no_segments_match_active_filter_message())
            await self._log_system_message(logging.INFO, self._log_no_filter_results_message(chat_id))
            return

        await self._handle_active_filter_segments_ok(
            chat_id=chat_id,
            series_name=series_name,
            outcome=outcome,
        )

    async def _do_handle_scene_segments(
            self,
            include_search_filter: bool = False,
    ) -> None:
        msg = self._message
        assert msg is not None
        chat_id = msg.get_chat_id()
        series_name = await self._get_user_active_series(msg.get_user_id())

        if len(msg.get_text().split()) > 1:
            await ActiveFilterTextCommandHandler._do_handle(self)
            return

        scene_outcome = await load_active_filter_scene_segments(
            chat_id=chat_id,
            series_name=series_name,
            logger=self._logger,
            size=self._active_filter_es_query_size(),
        )

        if scene_outcome.status == ActiveFilterSceneSegmentsStatus.NO_FILTER:
            await self._reply_error(get_no_filter_set_message())
            return

        if scene_outcome.status == ActiveFilterSceneSegmentsStatus.OK:
            outcome = ActiveFilterTextSegmentsOutcome(
                status=ActiveFilterTextSegmentsStatus.OK,
                search_filter=scene_outcome.search_filter if include_search_filter else None,
                segments=cast(List, scene_outcome.segments),
            )
            await self._handle_active_filter_segments_ok(
                chat_id=chat_id,
                series_name=series_name,
                outcome=outcome,
            )
            return

        await ActiveFilterTextCommandHandler._do_handle(self)
