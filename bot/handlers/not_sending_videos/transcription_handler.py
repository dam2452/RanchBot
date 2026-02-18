import logging
import math
from typing import (
    List,
    Optional,
    Tuple,
)

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import (
    get_log_no_segments_found_message,
    get_no_segments_found_message,
)
from bot.responses.not_sending_videos.transcription_handler_responses import (
    get_log_transcription_response_sent_message,
    get_no_quote_provided_message,
    get_transcription_response,
)
from bot.search.transcription_finder import TranscriptionFinder
from bot.services.scene_snap.scene_snap_service import SceneSnapService
from bot.types import TranscriptionContext
from bot.utils.constants import (
    EpisodeMetadataKeys,
    TranscriptionContextKeys,
)


class TranscriptionHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["transkrypcja", "transcription", "t"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_no_quote_provided_message(), math.inf)

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        quote = " ".join(args[1:])

        active_series = await self._get_user_active_series(self._message.get_user_id())

        result = await TranscriptionFinder.find_segment_with_context(quote, self._logger, active_series, context_size=15)

        if not result:
            return await self.__reply_no_segments_found(quote)

        snapped_start, snapped_end = await self.__snap_context_to_scene(result, active_series)

        await self._reply(
            get_transcription_response(quote, result, snapped_start, snapped_end),
            data={
                "quote": quote,
                "segment": result,
            },
        )

        return await self._log_system_message(
            logging.INFO,
            get_log_transcription_response_sent_message(quote, self._message.get_username()),
        )

    async def __snap_context_to_scene(
        self, result: TranscriptionContext, active_series: str,
    ) -> Tuple[Optional[float], Optional[float]]:
        overall_start = float(result[TranscriptionContextKeys.OVERALL_START_TIME])
        overall_end = float(result[TranscriptionContextKeys.OVERALL_END_TIME])

        target = result.get(TranscriptionContextKeys.TARGET, {})
        episode_metadata = target.get(
            EpisodeMetadataKeys.EPISODE_METADATA,
            target.get(EpisodeMetadataKeys.EPISODE_INFO, {}),
        )
        season = episode_metadata.get(EpisodeMetadataKeys.SEASON)
        episode_number = episode_metadata.get(EpisodeMetadataKeys.EPISODE_NUMBER)

        if season is None or episode_number is None:
            return None, None

        scene_cuts = await SceneSnapService.fetch_scene_cuts(active_series, season, episode_number, self._logger)
        if not scene_cuts:
            return None, None

        snapped_start, snapped_end = SceneSnapService.snap_boundaries(
            overall_start, overall_end, overall_start, overall_end, scene_cuts,
        )
        return snapped_start, snapped_end

    async def __reply_no_segments_found(self, quote: str) -> None:
        await self._reply_error(get_no_segments_found_message(quote))
        await self._log_system_message(logging.INFO, get_log_no_segments_found_message(quote))
