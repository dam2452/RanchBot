import json
import logging
import math
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import ValidatorFunctions
from bot.handlers.character_bot_handler import CharacterBotHandler
from bot.responses.not_sending_videos.characters_handler_responses import scene_to_search_segment
from bot.responses.sending_videos.character_clip_handler_responses import (
    get_log_character_clip_message,
    get_no_quote_provided_message,
    get_no_scenes_found_message,
)
from bot.search.video_frames_finder import CharacterFinder
from bot.settings import settings


class CharacterClipHandler(CharacterBotHandler):
    def get_commands(self) -> List[str]:
        return ["klippostac", "kp"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_no_quote_provided_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, math.inf)

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()[1:]
        user_id = self._message.get_user_id()
        series_name = await self._get_user_active_series(user_id)

        character, emotion_input, emotion_en = await self._find_character(args, series_name)
        if character is None:
            return

        if emotion_en:
            scenes = await CharacterFinder.get_scenes_by_character_and_emotion(
                character_name=character,
                emotion_en=emotion_en,
                series_name=series_name,
                logger=self._logger,
                size=settings.MAX_ES_RESULTS_QUICK,
            )
        else:
            scenes = await CharacterFinder.get_scenes_by_character(
                character_name=character,
                series_name=series_name,
                logger=self._logger,
                size=settings.MAX_ES_RESULTS_QUICK,
            )

        if not scenes:
            await self._reply_error(get_no_scenes_found_message(character, emotion_input))
            return

        segments = [scene_to_search_segment(scene) for scene in scenes]
        quote = f"{character} {emotion_input}".strip()
        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=quote,
            segments=json.dumps(segments),
        )

        if await self._send_top_segment_as_clip(segments[0], series_name):
            return

        await self._log_system_message(
            logging.INFO,
            get_log_character_clip_message(character, self._message.get_username()),
        )
