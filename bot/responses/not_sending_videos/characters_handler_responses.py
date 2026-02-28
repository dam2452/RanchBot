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

_PREVIEW_COUNT = 5


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


def _conf_str(value: Optional[float]) -> str:
    return f"{value * 100:.1f}%" if value is not None else "?"


def _format_scene_line(index: int, scene: CharacterScene, use_emotion_conf: bool) -> str:
    seg = format_segment(_scene_to_segment_dict(scene))
    conf = scene.get("emotion_confidence") if use_emotion_conf else scene.get("actor_confidence")
    title = seg.episode_title[:22]
    return f"{index:2}. {seg.episode_formatted}  {seg.time_formatted}  {title:<22}  {_conf_str(conf)}"


def format_characters_list(characters: List[CharacterWithEpisodeCount]) -> str:
    if not characters:
        return get_no_characters_message()
    sorted_chars = sorted(characters, key=lambda c: c["episode_count"], reverse=True)
    lines = [
        f"{i + 1:2}. {c['name'][:28]:<28}  {c['episode_count']:>3} odc."
        for i, c in enumerate(sorted_chars[:_PREVIEW_COUNT])
    ]
    body = "\n".join(lines) + "\n\nPelna lista: /pl"
    return BotResponse.info(f"POSTACIE ({len(characters)})", body)


def format_characters_list_full(characters: List[CharacterWithEpisodeCount]) -> str:
    sorted_chars = sorted(characters, key=lambda c: c["episode_count"], reverse=True)
    lines = [
        f"{i + 1:3}. {c['name']:<30}  {c['episode_count']:>3} odc."
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

    use_emotion_conf = emotion_filter is not None
    lines = [
        _format_scene_line(i + 1, scene, use_emotion_conf)
        for i, scene in enumerate(scenes[:_PREVIEW_COUNT])
    ]

    if emotion_filter:
        title = f"{character_name.upper()} | {emotion_filter.upper()} ({len(scenes)} scen)"
        hint = f"\n\nPelna lista: /pl {character_name} {emotion_filter}"
    else:
        title = f"{character_name.upper()} ({len(scenes)} scen)"
        hint = f"\n\nPelna lista: /pl {character_name}"

    return BotResponse.info(title, "\n".join(lines) + hint)


def format_character_scenes_full(
    character_name: str,
    scenes: List[CharacterScene],
    emotion_filter: Optional[str] = None,
) -> str:
    use_emotion_conf = emotion_filter is not None
    lines = [
        _format_scene_line(i + 1, scene, use_emotion_conf)
        for i, scene in enumerate(scenes)
    ]
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
