import json
import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.objects_handler_responses import object_scene_to_search_segment
from bot.responses.sending_videos.object_clip_handler_responses import (
    get_log_object_clip_message,
    get_no_object_provided_message,
    get_no_scenes_found_message,
    get_object_not_found_message,
)
from bot.search.video_frames import ObjectFinder
from bot.settings import settings


class ObjectClipHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["klipobiekt", "ko"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_no_object_provided_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1)

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()[1:]
        object_query = " ".join(args)
        user_id = self._message.get_user_id()
        series_name = await self._get_user_active_series(user_id)

        object_name = await ObjectFinder.find_best_matching_object(object_query, series_name, self._logger)
        if object_name is None:
            await self._reply_error(get_object_not_found_message(object_query))
            return

        scenes = await ObjectFinder.get_scenes_by_object(
            class_name=object_name,
            series_name=series_name,
            logger=self._logger,
        )

        if not scenes:
            await self._reply_error(get_no_scenes_found_message(object_name))
            return

        segments = [object_scene_to_search_segment(scene) for scene in scenes][:settings.MAX_ES_RESULTS_QUICK]
        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=object_query,
            segments=json.dumps(segments),
        )

        if await self._send_top_segment_as_clip(segments[0], series_name):
            await self._log_system_message(
                logging.INFO,
                get_log_object_clip_message(object_name, self._message.get_username()),
            )
