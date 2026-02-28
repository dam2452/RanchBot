from typing import (
    Any,
    Dict,
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
from bot.utils.functions import (
    convert_number_to_emoji,
    format_segment,
)

_PREVIEW_COUNT = 5
_FRAME_SPAN_S = 3.0


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


def scene_to_search_segment(scene: CharacterScene) -> Dict[str, Any]:
    timestamp = scene["start_time"]
    return {
        SegmentKeys.START_TIME: max(0.0, timestamp - _FRAME_SPAN_S),
        SegmentKeys.END_TIME: timestamp + _FRAME_SPAN_S,
        SegmentKeys.VIDEO_PATH: scene.get("video_path", ""),
        EpisodeMetadataKeys.EPISODE_METADATA: {
            EpisodeMetadataKeys.SEASON: scene["season"],
            EpisodeMetadataKeys.EPISODE_NUMBER: scene["episode_number"],
            EpisodeMetadataKeys.TITLE: scene["title"],
        },
    }


def format_characters_list(characters: List[CharacterWithEpisodeCount]) -> str:
    if not characters:
        return get_no_characters_message()
    sorted_chars = sorted(characters, key=lambda c: c["episode_count"], reverse=True)
    lines = [
        f"{convert_number_to_emoji(i + 1)}  | 👤 {c['name']} | 🎬 w {c['episode_count']} odcinkach"
        for i, c in enumerate(sorted_chars[:_PREVIEW_COUNT])
    ]
    body = f"Lacznie: {convert_number_to_emoji(len(sorted_chars))} postaci\n\n" + "\n".join(lines) + "\n\nPelna lista: /pl"
    return BotResponse.info("POSTACIE", body)


def format_characters_list_full(characters: List[CharacterWithEpisodeCount]) -> str:
    sorted_chars = sorted(characters, key=lambda c: c["episode_count"], reverse=True)
    lines = [
        f"{i + 1:3}. {c['name']:<30}  w {c['episode_count']} odcinkach"
        for i, c in enumerate(sorted_chars)
    ]
    return f"POSTACIE ({len(sorted_chars)})\n\n" + "\n".join(lines)


def format_character_scenes(
    character_name: str,
    scenes: List[CharacterScene],
    emotion_filter: Optional[str] = None,
) -> str:
    if not scenes:
        msg = (
            f"Nie znaleziono scen z postacia '{character_name}' i emocja '{emotion_filter}'."
            if emotion_filter
            else f"Nie znaleziono scen z postacia '{character_name}'."
        )
        return BotResponse.warning("BRAK WYNIKOW", msg)

    def _scene_line(idx: int, scene: CharacterScene) -> str:
        seg = format_segment(_scene_to_segment_dict(scene))
        return f"{convert_number_to_emoji(idx)}  | 📺 {seg.episode_formatted} | 🕒 {seg.time_formatted}"

    lines = [_scene_line(i + 1, scene) for i, scene in enumerate(scenes[:_PREVIEW_COUNT])]

    count_line = f"Znaleziono: {convert_number_to_emoji(len(scenes))} scen"
    if emotion_filter:
        count_line += f"  |  Emocja: {emotion_filter}"

    hint = (
        f"Pelna lista: /pl {character_name} {emotion_filter}"
        if emotion_filter
        else f"Pelna lista: /pl {character_name}"
    )
    body = count_line + "\n\n" + "\n".join(lines) + "\n\n" + hint
    return BotResponse.info(f"POSTAC: {character_name.upper()}", body)


def format_character_scenes_full(
    character_name: str,
    scenes: List[CharacterScene],
    emotion_filter: Optional[str] = None,
) -> str:
    lines = []
    for i, scene in enumerate(scenes):
        seg = format_segment(_scene_to_segment_dict(scene))
        lines.append(f"{i + 1:4}. {seg.episode_formatted}  {seg.time_formatted}")
    if emotion_filter:
        header = f"{character_name.upper()} - {emotion_filter.upper()} ({len(scenes)} scen)\n\n"
    else:
        header = f"{character_name.upper()} ({len(scenes)} scen)\n\n"
    return header + "\n".join(lines)


def get_invalid_args_count_message() -> str:
    return BotResponse.usage(
        command="postacie",
        error_title="ZA DUZO ARGUMENTOW",
        usage_syntax="[postac] [emocja]",
        params=[
            ("[postac]", "nazwa postaci (opcjonalna, fuzzy)"),
            ("[emocja]", "emocja po polsku lub angielsku (opcjonalna, wymaga podania postaci)"),
        ],
        example="/postacie Michalowa radosny",
    )


def get_no_characters_message() -> str:
    return BotResponse.warning("BRAK DANYCH", "Brak postaci w danych.")


def get_log_characters_list_message(count: int, username: str) -> str:
    return f"Characters list ({count} items) sent to user {username}."


def get_log_character_scenes_message(character: str, count: int, username: str) -> str:
    return f"Character '{character}' scenes ({count} items) sent to user {username}."
