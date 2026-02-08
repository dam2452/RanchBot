import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.my_clips_handler_responses import (
    format_myclips_response,
    get_log_no_saved_clips_message,
    get_log_saved_clips_sent_message,
    get_no_saved_clips_message,
)
from bot.search.transcription_finder import TranscriptionFinder


class MyClipsHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["mojeklipy", "myclips", "mk"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    async def _do_handle(self) -> None:
        user_id = self._message.get_user_id()

        clips = await DatabaseManager.get_saved_clips(user_id)
        if not clips:
            return await self.__reply_no_saved_clips()

        active_series = await self._get_user_active_series(user_id)

        season_info = await TranscriptionFinder.get_season_details_from_elastic(
            logger=self._logger,
            series_name=active_series,
        )

        await self._reply(
            format_myclips_response(
                clips=clips,
                username=self._message.get_username(),
                full_name=self._message.get_full_name(),
                season_info=season_info,
            ),
            data={
                "clips": [clip.to_dict() for clip in clips],
                "season_info": season_info,
            },
        )

        return await self._log_system_message(
            logging.INFO,
            get_log_saved_clips_sent_message(self._message.get_username()),
        )

    async def __reply_no_saved_clips(self) -> None:
        await self._reply(get_no_saved_clips_message(), data={"clips": []})

        await self._log_system_message(logging.INFO, get_log_no_saved_clips_message(self._message.get_username()))
