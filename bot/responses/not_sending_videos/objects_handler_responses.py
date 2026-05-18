from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from aiogram.utils.markdown import markdown_decoration

from bot.responses.bot_response import BotResponse
from bot.search.video_frames import get_polish_name
from bot.types import (
    Language,
    ObjectScene,
    ObjectWithCount,
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


def object_scene_to_search_segment(scene: ObjectScene) -> Dict[str, Any]:
    start_time = scene["start_time"]
    end_time = scene["end_time"]
    if start_time == end_time:
        start_time = max(0.0, start_time - _FRAME_SPAN_S)
        end_time = end_time + _FRAME_SPAN_S
    return {
        SegmentKeys.START_TIME: start_time,
        SegmentKeys.END_TIME: end_time,
        SegmentKeys.VIDEO_PATH: scene.get("video_path", ""),
        EpisodeMetadataKeys.EPISODE_METADATA: {
            EpisodeMetadataKeys.SEASON: scene["season"],
            EpisodeMetadataKeys.EPISODE_NUMBER: scene["episode_number"],
            EpisodeMetadataKeys.TITLE: scene["title"],
        },
    }


def format_objects_list(objects: List[ObjectWithCount], lang: Language = "pl") -> str:
    if not objects:
        return get_no_objects_message(lang)
    sorted_objs = sorted(objects, key=lambda o: o["scene_count"], reverse=True)
    if lang == "en":
        lines = [
            f"{convert_number_to_emoji(i + 1)} {o['class_name']}\n  🎬 appeared in {o['scene_count']} scenes"
            for i, o in enumerate(sorted_objs[:_PREVIEW_COUNT])
        ]
        body = (
            f"Total: {convert_number_to_emoji(len(sorted_objs))} objects\n\n"
            + "\n".join(lines)
            + "\n\n👉 Full list: /objl_en"
        )
        return BotResponse.info("OBJECTS", body)
    lines = [
        f"{convert_number_to_emoji(i + 1)} {get_polish_name(o['class_name'])}\n  🎬 wystąpił w {o['scene_count']} scenach"
        for i, o in enumerate(sorted_objs[:_PREVIEW_COUNT])
    ]
    body = (
        f"Łącznie: {convert_number_to_emoji(len(sorted_objs))} obiektów\n\n"
        + "\n".join(lines)
        + "\n\n👉 Pełna lista: /objl"
    )
    return BotResponse.info("OBIEKTY", body)


def format_objects_list_full(objects: List[ObjectWithCount], lang: Language = "pl") -> str:
    sorted_objs = sorted(objects, key=lambda o: o["scene_count"], reverse=True)
    if lang == "en":
        lines = [
            f"{i + 1:3}. {o['class_name']:<30}  appeared in {o['scene_count']} scenes"
            for i, o in enumerate(sorted_objs)
        ]
        return f"OBJECTS ({len(sorted_objs)})\n\n" + "\n".join(lines)
    lines = [
        f"{i + 1:3}. {get_polish_name(o['class_name']):<30}  wystąpił w {o['scene_count']} scenach"
        for i, o in enumerate(sorted_objs)
    ]
    return f"OBIEKTY ({len(sorted_objs)})\n\n" + "\n".join(lines)


def format_object_scenes(
    class_name: str,
    scenes: List[ObjectScene],
    qty_filter_str: Optional[str] = None,
    lang: Language = "pl",
) -> str:
    display_name = class_name if lang == "en" else get_polish_name(class_name)
    filter_info = f" (filter: {qty_filter_str})" if qty_filter_str and lang == "en" else (f" (filtr: {qty_filter_str})" if qty_filter_str else "")
    if not scenes:
        if lang == "en":
            msg = f"No scenes found with object '{display_name}'{filter_info}."
            return BotResponse.warning("NO RESULTS", msg)
        msg = f"Nie znaleziono scen z obiektem '{display_name}'{filter_info}."
        return BotResponse.warning("BRAK WYNIKÓW", msg)

    def _scene_line(idx: int, scene: ObjectScene) -> str:
        seg = format_segment(scene_to_segment_dict(scene))
        return (
            f"{convert_number_to_emoji(idx)}  | 📺 {seg.episode_formatted} | 🕒 {seg.time_formatted} | x{scene['total_count']}\n"
            f"   👉  {seg.episode_title}"
        )

    lines = [_scene_line(i + 1, scene) for i, scene in enumerate(scenes[:_PREVIEW_COUNT])]
    count_emoji = convert_number_to_emoji(len(scenes))

    if lang == "en":
        header = f"🎯 *Object: {markdown_decoration.quote(display_name)}* 🎯\n"
        if qty_filter_str:
            header += f"🔢 *Filter: {markdown_decoration.quote(qty_filter_str)}* 🔢\n"
        header += f"👁️ *Found:* {count_emoji} scenes 👁️\n\n"
        hint = (
            f"\n\n\n👉 Full list: /objl_en {display_name} {qty_filter_str}"
            if qty_filter_str
            else f"\n\n\n👉 Full list: /objl_en {display_name}"
        )
        code_header = f"Object:\u00A0{display_name}".replace(" ", "\u00A0")
    else:
        header = f"🎯 *Obiekt: {markdown_decoration.quote(display_name)}* 🎯\n"
        if qty_filter_str:
            header += f"🔢 *Filtr: {markdown_decoration.quote(qty_filter_str)}* 🔢\n"
        header += f"👁️ *Znaleziono:* {count_emoji} scen 👁️\n\n"
        hint = (
            f"\n\n\n👉 Pełna lista: /objl {display_name} {qty_filter_str}"
            if qty_filter_str
            else f"\n\n\n👉 Pełna lista: /objl {display_name}"
        )
        code_header = f"Obiekt:\u00A0{display_name}".replace(" ", "\u00A0")
    return header + f"```{code_header}\n\n" + "\n\n".join(lines) + hint + "\n```"


def format_object_scenes_full(
    class_name: str,
    scenes: List[ObjectScene],
    qty_filter_str: Optional[str] = None,
    lang: Language = "pl",
) -> str:
    display_name = class_name if lang == "en" else get_polish_name(class_name)
    lines = []
    for i, scene in enumerate(scenes):
        seg = format_segment(scene_to_segment_dict(scene))
        lines.append(
            f"{i + 1:4}. {seg.episode_formatted}  {seg.time_formatted}  x{scene['total_count']}",
        )
    scenes_word = "scenes" if lang == "en" else "scen"
    if qty_filter_str:
        header = f"{display_name.upper()} - {qty_filter_str} ({len(scenes)} {scenes_word})\n\n"
    else:
        header = f"{display_name.upper()} ({len(scenes)} {scenes_word})\n\n"
    return header + "\n".join(lines)


def get_no_objects_message(lang: Language = "pl") -> str:
    if lang == "en":
        return BotResponse.warning("NO DATA", "No objects in the database.")
    return BotResponse.warning("BRAK DANYCH", "Brak obiektów w bazie danych.")


def get_object_not_found_message(query: str, lang: Language = "pl") -> str:
    if lang == "en":
        return BotResponse.warning("NO RESULTS", f"No object matching '{query}' found.")
    return BotResponse.warning("BRAK WYNIKÓW", f"Nie znaleziono obiektu pasującego do '{query}'.")


def get_invalid_quantity_filter_message(raw: str) -> str:
    return BotResponse.usage(
        command="obj",
        error_title="NIEPOPRAWNY FILTR",
        usage_syntax="<nazwa_obiektu> <filtr>",
        params=[
            ("<filtr>", "liczba lub operator z liczbą: =4, >4, <4, >=4, <=4"),
        ],
        example=f"/obj {raw} >3",
    )


def get_log_objects_list_message(count: int, username: str) -> str:
    return f"Objects list ({count} items) sent to user {username}."


def get_log_object_scenes_message(class_name: str, count: int, username: str) -> str:
    return f"Object '{class_name}' scenes ({count} items) sent to user {username}."
