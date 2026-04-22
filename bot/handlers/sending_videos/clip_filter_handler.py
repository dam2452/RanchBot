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
from bot.responses.filter_command_messages import (
    get_no_filter_set_message,
    get_no_segments_match_active_filter_message,
)
from bot.responses.sending_videos.clip_filter_handler_responses import (
    get_clip_filter_usage_message,
    get_log_clip_filter_no_results_message,
    get_log_clip_filter_success_message,
)
from bot.responses.sending_videos.clip_handler_responses import (
    get_log_clip_success_message,
    get_log_segment_saved_message,
    get_no_segments_found_message,
)
from bot.services.scene_snap.scene_snap_service import SceneSnapService
from bot.services.search_filter.active_filter_scene_segments import (
    ActiveFilterSceneSegmentsStatus,
    load_active_filter_scene_segments,
)
from bot.services.search_filter.active_filter_text_segments import (
    ActiveFilterTextSegmentsOutcome,
    ActiveFilterTextSegmentsStatus,
)
from bot.settings import settings
from bot.utils.constants import SegmentKeys
from bot.video.clips_extractor import ClipsExtractor


class ClipFilterHandler(ActiveFilterTextCommandHandler):
    def get_commands(self) -> List[str]:
        return ["klipfiltr", "clipfilter", "kf"]

    def _active_filter_es_query_size(self) -> int:
        return 1000

    def _log_no_filter_results_message(self, chat_id: int) -> str:
        return get_log_clip_filter_no_results_message(chat_id)

    def _get_usage_message(self) -> str:
        return get_clip_filter_usage_message()

    async def _do_handle(self) -> None:
        msg = self._message
        assert msg is not None
        chat_id = msg.get_chat_id()
        series_name = await self._get_user_active_series(msg.get_user_id())

        content = msg.get_text().split()
        if len(content) > 1:
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
                    segments=scene_outcome.segments,
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
            default_es_size=settings.MAX_ES_RESULTS_QUICK,
            error_message=get_no_segments_found_message(),
        )
        if not segments:
            return

        await DatabaseManager.insert_last_search(
            chat_id=chat_id,
            quote=quote,
            segments=json.dumps(segments),
        )


        segment = cast(Dict[str, Any], segments[0])
        start_time = max(0, segment[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE)
        end_time = segment[SegmentKeys.END_TIME] + settings.EXTEND_AFTER

        start_time, end_time = await SceneSnapService.snap_clip_times(
            series_name, segment, start_time, end_time, self._logger,
        )

        segment_id = segment.get(SegmentKeys.SEGMENT_ID, segment.get(SegmentKeys.ID))
        start_time, end_time, clip_duration = await self._trim_clip_if_needed(
            start_time=start_time,
            end_time=end_time,
            segment_id=segment_id,
        )

        output_filename = await ClipsExtractor.extract_clip(
            segment[SegmentKeys.VIDEO_PATH], start_time, end_time, self._logger,
        )

        await self._responder.send_video(
            output_filename,
            duration=clip_duration,
            suggestions=["Uzyj /w N aby wybrac inny wynik"],
        )

        await self._insert_last_single_clip(
            chat_id=chat_id,
            segment=segment,
            start_time=start_time,
            end_time=end_time,
        )

        await self._log_system_message(logging.INFO, get_log_segment_saved_message(chat_id))
        await self._log_system_message(logging.INFO, get_log_clip_success_message(msg.get_username()))

    async def _handle_active_filter_segments_ok(
            self,
            *,
            chat_id: int,
            series_name: str,
            outcome: ActiveFilterTextSegmentsOutcome,
    ) -> None:
        filtered = outcome.segments

        await DatabaseManager.insert_last_search(
            chat_id=chat_id,
            quote="/klipfiltr",
            segments=json.dumps(filtered),
        )

        top_segment = cast(Dict[str, Any], filtered[0])
        if await self._send_top_segment_as_clip(top_segment, series_name):
            return

        msg = self._message
        assert msg is not None
        await self._log_system_message(
            logging.INFO,
            get_log_clip_filter_success_message(chat_id, msg.get_username()),
        )
