import logging
from typing import (
    List,
    Optional,
    Tuple,
)

from bot.responses.not_sending_videos.characters_handler_responses import parse_character_args
from bot.search.character_finder import CharacterFinder


class CharacterHandlerMixin:
    _logger: logging.Logger

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
            await self._reply_error(f"Nie znaleziono postaci pasujących do '{character_query}'.")  # pylint: disable=no-member
            return None, emotion_input, emotion_en
        return character, emotion_input, emotion_en
