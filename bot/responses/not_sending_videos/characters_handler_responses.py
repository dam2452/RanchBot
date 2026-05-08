from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from aiogram.utils.markdown import markdown_decoration

from bot.responses.bot_response import BotResponse
from bot.types import (
    CharacterScene,
    CharacterWithEpisodeCount,
    Language,
)
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.utils.functions import (
    convert_number_to_emoji,
    format_segment,
    scene_to_segment_dict,
)

_PREVIEW_COUNT = 5
_FRAME_SPAN_S = 3.0


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


def format_characters_list(characters: List[CharacterWithEpisodeCount], lang: Language = "pl") -> str:
    if not characters:
        return get_no_characters_message(lang)
    sorted_chars = sorted(characters, key=lambda c: c["episode_count"], reverse=True)
    if lang == "en":
        lines = [
            f"{convert_number_to_emoji(i + 1)} 👤 {c['name']}\n  🎬 appeared in {c['episode_count']} episodes"
            for i, c in enumerate(sorted_chars[:_PREVIEW_COUNT])
        ]
        body = f"Total: {convert_number_to_emoji(len(sorted_chars))} characters\n\n" + "\n".join(lines) + "\n\n👉 Full list: /pl_en"
        return BotResponse.info("CHARACTERS", body)
    lines = [
        f"{convert_number_to_emoji(i + 1)} 👤 {c['name']}\n  🎬 wystąpił w {c['episode_count']} odcinkach"
        for i, c in enumerate(sorted_chars[:_PREVIEW_COUNT])
    ]
    body = f"Łącznie: {convert_number_to_emoji(len(sorted_chars))} postaci\n\n" + "\n".join(lines) + "\n\n👉 Pełna lista: /pl"
    return BotResponse.info("POSTACIE", body)


def format_characters_list_full(characters: List[CharacterWithEpisodeCount], lang: Language = "pl") -> str:
    sorted_chars = sorted(characters, key=lambda c: c["episode_count"], reverse=True)
    if lang == "en":
        lines = [
            f"{i + 1:3}. {c['name']:<30}  appeared in {c['episode_count']} episodes"
            for i, c in enumerate(sorted_chars)
        ]
        return f"CHARACTERS ({len(sorted_chars)})\n\n" + "\n".join(lines)
    lines = [
        f"{i + 1:3}. {c['name']:<30}  wystąpił w {c['episode_count']} odcinkach"
        for i, c in enumerate(sorted_chars)
    ]
    return f"POSTACIE ({len(sorted_chars)})\n\n" + "\n".join(lines)


def format_character_scenes(
    character_name: str,
    scenes: List[CharacterScene],
    emotion_filter: Optional[str] = None,
    lang: Language = "pl",
) -> str:
    if not scenes:
        if lang == "en":
            msg = (
                f"No scenes found for character '{character_name}' with emotion '{emotion_filter}'."
                if emotion_filter
                else f"No scenes found for character '{character_name}'."
            )
            return BotResponse.warning("NO RESULTS", msg)
        msg = (
            f"Nie znaleziono scen z postacią '{character_name}' i emocją '{emotion_filter}'."
            if emotion_filter
            else f"Nie znaleziono scen z postacią '{character_name}'."
        )
        return BotResponse.warning("BRAK WYNIKÓW", msg)

    def _scene_line(idx: int, scene: CharacterScene) -> str:
        seg = format_segment(scene_to_segment_dict(scene))
        return (
            f"{convert_number_to_emoji(idx)}  | 📺 {seg.episode_formatted} | 🕒 {seg.time_formatted}\n"
            f"   👉  {seg.episode_title}"
        )

    lines = [_scene_line(i + 1, scene) for i, scene in enumerate(scenes[:_PREVIEW_COUNT])]
    count_emoji = convert_number_to_emoji(len(scenes))

    if lang == "en":
        header = f"🎭 *Character: {markdown_decoration.quote(character_name)}* 🎭\n"
        if emotion_filter:
            header += f"😊 *Emotion: {markdown_decoration.quote(emotion_filter)}* 😊\n"
        header += f"👁️ *Found:* {count_emoji} scenes 👁️\n\n"
        hint = (
            f"\n\n\n👉 Full list: /pl_en {character_name} {emotion_filter}"
            if emotion_filter
            else f"\n\n\n👉 Full list: /pl_en {character_name}"
        )
        code_header = f"Character:\u00A0{character_name}".replace(" ", "\u00A0")
    else:
        header = f"🎭 *Postać: {markdown_decoration.quote(character_name)}* 🎭\n"
        if emotion_filter:
            header += f"😊 *Emocja: {markdown_decoration.quote(emotion_filter)}* 😊\n"
        header += f"👁️ *Znaleziono:* {count_emoji} scen 👁️\n\n"
        hint = (
            f"\n\n\n👉 Pełna lista: /pl {character_name} {emotion_filter}"
            if emotion_filter
            else f"\n\n\n👉 Pełna lista: /pl {character_name}"
        )
        code_header = f"Postać:\u00A0{character_name}".replace(" ", "\u00A0")
    return header + f"```{code_header}\n\n" + "\n\n".join(lines) + hint + "\n```"


def format_character_scenes_full(
    character_name: str,
    scenes: List[CharacterScene],
    emotion_filter: Optional[str] = None,
    lang: Language = "pl",
) -> str:
    lines = []
    for i, scene in enumerate(scenes):
        seg = format_segment(scene_to_segment_dict(scene))
        lines.append(f"{i + 1:4}. {seg.episode_formatted}  {seg.time_formatted}")
    scenes_word = "scenes" if lang == "en" else "scen"
    if emotion_filter:
        header = f"{character_name.upper()} - {emotion_filter.upper()} ({len(scenes)} {scenes_word})\n\n"
    else:
        header = f"{character_name.upper()} ({len(scenes)} {scenes_word})\n\n"
    return header + "\n".join(lines)


def get_invalid_args_count_message() -> str:
    return BotResponse.usage(
        command="postacie",
        error_title="ZA DUŻO ARGUMENTÓW",
        usage_syntax="[postać] [emocja]",
        params=[
            ("[postać]", "nazwa postaci (opcjonalna, fuzzy)"),
            ("[emocja]", "emocja po polsku lub angielsku (opcjonalna, wymaga podania postaci)"),
        ],
        example="/postacie Michałowa radosny",
    )


def get_no_characters_message(lang: Language = "pl") -> str:
    if lang == "en":
        return BotResponse.warning("NO DATA", "No characters in the database.")
    return BotResponse.warning("BRAK DANYCH", "Brak postaci w bazie danych.")


def get_character_not_found_message(query: str) -> str:
    return BotResponse.warning("BRAK WYNIKÓW", f"Nie znaleziono postaci pasujących do '{query}'.")


def get_log_characters_list_message(count: int, username: str) -> str:
    return f"Characters list ({count} items) sent to user {username}."


def get_log_character_scenes_message(character: str, count: int, username: str) -> str:
    return f"Character '{character}' scenes ({count} items) sent to user {username}."
