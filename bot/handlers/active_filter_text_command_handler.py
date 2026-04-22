from abc import abstractmethod
import logging

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.filter_command_messages import (
    get_no_filter_set_message,
    get_no_segments_match_active_filter_message,
)
from bot.services.search_filter.active_filter_text_segments import (
    ActiveFilterTextSegmentsOutcome,
    ActiveFilterTextSegmentsStatus,
    load_active_filter_text_segments,
)


class ActiveFilterTextCommandHandler(BotMessageHandler):
    """Wspólna obsługa komend opartych wyłącznie o aktywny `/filtr` (tekst z ES + FilterApplicator)."""

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    def _get_usage_message(self) -> str:
        return get_no_filter_set_message()

    @abstractmethod
    def _active_filter_es_query_size(self) -> int:
        """Rozmiar zapytania ES w `find_segments_by_filter_only`."""

    @abstractmethod
    def _log_no_filter_results_message(self, chat_id: int) -> str:
        """Komunikat logu przy braku kandydatów lub po post-filtrze."""

    @abstractmethod
    async def _handle_active_filter_segments_ok(
            self,
            *,
            chat_id: int,
            series_name: str,
            outcome: ActiveFilterTextSegmentsOutcome,
    ) -> None:
        """Wywoływane gdy `outcome.status` jest OK (segmenty gotowe do dalszej obsługi)."""

    async def _do_handle(self) -> None:
        msg = self._message
        chat_id = msg.get_chat_id()
        series_name = await self._get_user_active_series(msg.get_user_id())

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
