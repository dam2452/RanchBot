from typing import (
    List,
    Optional,
    Tuple,
)

from bot.handlers.bot_message_handler import BotMessageHandler
from bot.responses.not_sending_videos.characters_handler_responses import (
    get_character_not_found_message,
    parse_character_args,
)
from bot.search.video_frames import CharacterFinder


class CharacterBotHandler(BotMessageHandler):
    async def _find_character(
        self,
        args: List[str],
        series_name: str,
    ) -> Tuple[Optional[str], str, str]:
        character_query, emotion_input, emotion_en = parse_character_args(args)
        character = await CharacterFinder.find_best_matching_name(
            character_query, series_name, self._logger,
        )
        if character is None:
            await self._reply_error(get_character_not_found_message(character_query))
            return None, emotion_input, emotion_en
        return character, emotion_input, emotion_en
