import logging
from typing import (
    List,
    Optional,
    Tuple,
)

from bot.responses.not_sending_videos.characters_handler_responses import parse_character_args
from bot.search.video_frames import CharacterFinder


async def find_character(
    args: List[str],
    series_name: str,
    logger: logging.Logger,
) -> Tuple[Optional[str], str, str, str]:
    character_query, emotion_input, emotion_en = parse_character_args(args)
    character = await CharacterFinder.find_best_matching_name(character_query, series_name, logger)
    return character, character_query, emotion_input, emotion_en
