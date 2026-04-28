import json
import logging
from typing import (
    Any,
    Dict,
    List,
    cast,
)

from bot.database.database_manager import DatabaseManager
from bot.handlers.active_filter_text_command_handler import ActiveFilterTextCommandHandler
from bot.responses.bot_message_handler_responses import get_no_segments_found_message
from bot.responses.filter_command_messages import (
    get_no_filter_set_message,
    get_no_segments_match_active_filter_message,
)
from bot.responses.not_sending_videos.search_filter_handler_responses import (
    format_search_filter_response,
    get_log_search_filter_no_results_message,
    get_log_search_filter_results_sent_message,
)
from bot.responses.not_sending_videos.search_handler_responses import format_search_response
from bot.services.search_filter.active_filter_scene_segments import (
    ActiveFilterSceneSegmentsStatus,
    load_active_filter_scene_segments,
)
from bot.services.search_filter.active_filter_text_segments import (
    ActiveFilterTextSegmentsOutcome,
    ActiveFilterTextSegmentsStatus,
)
from bot.settings import settings


class SearchFilterHandler(ActiveFilterTextCommandHandler):
    def get_commands(self) -> List[str]:
        return ["szukajfiltr", "searchfilter", "szf"]

    def _active_filter_es_query_size(self) -> int:
        return settings.MAX_ES_RESULTS_LONG

    def _log_no_filter_results_message(self, chat_id: int) -> str:
        return get_log_search_filter_no_results_message(chat_id)

    async def _do_handle(self) -> None:
        msg = self._message
        assert msg is not None
        chat_id = msg.get_chat_id()
        series_name = await self._get_user_active_series(msg.get_user_id())

        if len(msg.get_text().split()) > 1:
            await super()._do_handle()
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
            await self._handle_active_filter_segments_ok(
                chat_id=chat_id,
                series_name=series_name,
                outcome=ActiveFilterTextSegmentsOutcome(
                    status=ActiveFilterTextSegmentsStatus.OK,
                    search_filter=scene_outcome.search_filter,
                    segments=cast(list, scene_outcome.segments),
                ),
            )
            return

        if scene_outcome.status == ActiveFilterSceneSegmentsStatus.NO_MATCHES:
            await self._reply_error(get_no_segments_match_active_filter_message())
            await self._log_system_message(
                logging.INFO,
                self._log_no_filter_results_message(chat_id),
            )
            return

        await super()._do_handle()

    async def _handle_with_quote(
            self,
            quote: str,
            chat_id: int,
            series_name: str,
            msg: Any,
    ) -> None:
        segments = await self._search_with_active_filter(
            quote=quote,
            chat_id=chat_id,
            series_name=series_name,
            default_es_size=settings.MAX_ES_RESULTS_LONG,
            error_message=get_no_segments_found_message(quote),
        )
        if not segments:
            return

        response = format_search_response(len(segments), segments, quote)

        await self._handle_search_results(
            chat_id=chat_id,
            quote=quote,
            segments=segments,
            response_text=response,
            log_message=f"Search-by-filter with quote '{quote}' results ({len(segments)}) sent to user '{msg.get_username()}'.",
        )

    async def _handle_active_filter_segments_ok(
            self,
            *,
            chat_id: int,
            series_name: str,
            outcome: ActiveFilterTextSegmentsOutcome,
    ) -> None:
        _ = series_name
        msg = self._message
        segments = outcome.segments

        await DatabaseManager.insert_last_search(
            chat_id=chat_id,
            quote="/szukajfiltr",
            segments=json.dumps(segments),
        )

        response = format_search_filter_response(
            len(segments), cast(List[Dict[str, Any]], segments),
        )
        await self._reply(
            response,
            data={
                "filter": outcome.search_filter,
                "results": segments,
            },
        )
        await self._log_system_message(
            logging.INFO,
            get_log_search_filter_results_sent_message(msg.get_username(), len(segments)),
        )
