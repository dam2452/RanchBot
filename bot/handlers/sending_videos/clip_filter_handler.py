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
from bot.responses.sending_videos.clip_filter_handler_responses import (
    get_log_clip_filter_no_results_message,
    get_log_clip_filter_success_message,
)
from bot.services.search_filter.active_filter_text_segments import ActiveFilterTextSegmentsOutcome


class ClipFilterHandler(ActiveFilterTextCommandHandler):
    def get_commands(self) -> List[str]:
        return ["klipfiltr", "clipfilter", "kf"]

    def _active_filter_es_query_size(self) -> int:
        return 1000

    def _log_no_filter_results_message(self, chat_id: int) -> str:
        return get_log_clip_filter_no_results_message(chat_id)

    async def _handle_active_filter_segments_ok(
            self,
            *,
            chat_id: int,
            series_name: str,
            outcome: ActiveFilterTextSegmentsOutcome,
    ) -> None:
        msg = self._message
        filtered = outcome.segments

        await DatabaseManager.insert_last_search(
            chat_id=chat_id,
            quote="/klipfiltr",
            segments=json.dumps(filtered),
        )

        top_segment = cast(Dict[str, Any], filtered[0])
        if await self._send_top_segment_as_clip(top_segment, series_name):
            return

        await self._log_system_message(
            logging.INFO,
            get_log_clip_filter_success_message(chat_id, msg.get_username()),
        )
