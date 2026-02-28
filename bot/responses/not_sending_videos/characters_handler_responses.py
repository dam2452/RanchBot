from typing import (
    List,
    Optional,
)

from bot.responses.bot_response import BotResponse
from bot.types import (
    CharacterScene,
    CharacterWithEpisodeCount,
)
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.utils.functions import format_segment


def _scene_to_segment_dict(scene: CharacterScene) -> dict:
    return {
        EpisodeMetadataKeys.EPISODE_METADATA: {
            EpisodeMetadataKeys.SEASON: scene["season"],
            EpisodeMetadataKeys.EPISODE_NUMBER: scene["episode_number"],
            EpisodeMetadataKeys.TITLE: scene["title"],
        },
        SegmentKeys.START_TIME: scene["start_time"],
        SegmentKeys.END_TIME: scene["end_time"],
    }


def format_characters_list(characters: List[CharacterWithEpisodeCount]) -> str:
    if not characters:
        return get_no_characters_message()
    header = f"Postacie ({len(characters)}):\n\n"
    header += f"{'Nr':<4} {'Postac':<20} {'Odcinki'}\n"
    header += "-" * 35 + "\n"
    lines = [
        f"{i + 1:<4} {c['name']:<20} {c['episode_count']}"
        for i, c in enumerate(characters)
    ]
    return header + "\n".join(lines)


def format_character_scenes(
    character_name: str,
    scenes: List[CharacterScene],
    emotion_filter: Optional[str] = None,
) -> str:
    if not scenes:
        if emotion_filter:
            return f"Nie znaleziono scen z postacia '{character_name}' i emocja '{emotion_filter}'."
        return f"Nie znaleziono scen z postacia '{character_name}'."

    filter_info = f" (emocja: {emotion_filter})" if emotion_filter else ""
    header = f"Sceny z postacia '{character_name}'{filter_info} ({len(scenes)}):\n\n"
    header += f"{'Nr':<4} {'Odcinek':<10} {'Czas':<8} {'Tytul'}\n"
    header += "-" * 50 + "\n"
    lines = []
    for i, scene in enumerate(scenes, start=1):
        segment_info = format_segment(_scene_to_segment_dict(scene))
        lines.append(
            f"{i:<4} {segment_info.episode_formatted:<10} {segment_info.time_formatted:<8} {segment_info.episode_title}",
        )
    return header + "\n".join(lines)


def get_invalid_args_count_message() -> str:
    return BotResponse.usage(
        command="postacie",
        error_title="ZA DUZO ARGUMENTOW",
        usage_syntax="[postac] [emocja]",
        params=[
            ("[postac]", "nazwa postaci (opcjonalna, case insensitive)"),
            ("[emocja]", "emocja po polsku lub angielsku (opcjonalna, wymaga podania postaci)"),
        ],
        example="/postacie Michałowa radosny",
    )


def get_no_characters_message() -> str:
    return "Brak postaci w danych."


def get_log_characters_list_message(count: int, username: str) -> str:
    return f"Characters list ({count} items) sent to user {username}."


def get_log_character_scenes_message(character: str, count: int, username: str) -> str:
    return f"Character '{character}' scenes ({count} items) sent to user {username}."
