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
from bot.responses.not_sending_videos.search_filter_handler_responses import (
    format_search_filter_response,
    get_log_search_filter_no_results_message,
    get_log_search_filter_results_sent_message,
)
from bot.services.search_filter.active_filter_text_segments import ActiveFilterTextSegmentsOutcome
from bot.settings import settings


class SearchFilterHandler(ActiveFilterTextCommandHandler):
    def get_commands(self) -> List[str]:
        return ["szukajfiltr", "searchfilter", "szf"]

    def _active_filter_es_query_size(self) -> int:
        return settings.MAX_ES_RESULTS_LONG

    def _log_no_filter_results_message(self, chat_id: int) -> str:
        return get_log_search_filter_no_results_message(chat_id)

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
