from typing import (
    List,
    Optional,
    Tuple,
)

from bot.handlers.bot_message_handler import BotMessageHandler
from bot.responses.not_sending_videos.characters_handler_responses import get_character_not_found_message
from bot.responses.not_sending_videos.emotions_handler_responses import map_emotion_to_en
from bot.search.video_frames import CharacterFinder


class CharacterBotHandler(BotMessageHandler):
    async def _find_character(
        self,
        args: List[str],
        series_name: str,
    ) -> Tuple[Optional[str], str, str]:
        full_query = " ".join(args)

        if len(args) >= 2:
            emotion_en = map_emotion_to_en(args[-1])
            if emotion_en:
                partial_query = " ".join(args[:-1])
                character = await CharacterFinder.find_best_matching_name(partial_query, series_name, self._logger)
                if character is not None:
                    return character, args[-1], emotion_en

        character = await CharacterFinder.find_best_matching_name(full_query, series_name, self._logger)
        if character is not None:
            return character, "", ""

        await self._reply_error(get_character_not_found_message(full_query))
        return None, "", ""
