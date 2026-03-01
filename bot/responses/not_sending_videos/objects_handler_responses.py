from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from bot.responses.bot_response import BotResponse
from bot.types import (
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
)

_PREVIEW_COUNT = 5


def _scene_to_segment_dict(scene: ObjectScene) -> Dict[str, Any]:
    return {
        EpisodeMetadataKeys.EPISODE_METADATA: {
            EpisodeMetadataKeys.SEASON: scene["season"],
            EpisodeMetadataKeys.EPISODE_NUMBER: scene["episode_number"],
            EpisodeMetadataKeys.TITLE: scene["title"],
        },
        SegmentKeys.START_TIME: scene["start_time"],
        SegmentKeys.END_TIME: scene["end_time"],
    }


def format_objects_list(objects: List[ObjectWithCount]) -> str:
    if not objects:
        return get_no_objects_message()
    lines = [
        f"{convert_number_to_emoji(i + 1)} {o['class_name']}\n  🔢 {o['frame_count']} klatek"
        for i, o in enumerate(objects[:_PREVIEW_COUNT])
    ]
    body = f"Łącznie: {convert_number_to_emoji(len(objects))} obiektów\n\n" + "\n".join(lines) + "\n\n👉 Pełna lista: /obj <nazwa>"
    return BotResponse.info("OBIEKTY", body)


def format_object_scenes(
    class_name: str,
    scenes: List[ObjectScene],
    qty_filter_str: Optional[str] = None,
) -> str:
    filter_info = f" (filtr: {qty_filter_str})" if qty_filter_str else ""
    if not scenes:
        msg = f"Nie znaleziono scen z obiektem '{class_name}'{filter_info}."
        return BotResponse.warning("BRAK WYNIKÓW", msg)

    def _scene_line(idx: int, scene: ObjectScene) -> str:
        seg = format_segment(_scene_to_segment_dict(scene))
        return (
            f"{convert_number_to_emoji(idx)}  | 📺 {seg.episode_formatted} | 🕒 {seg.time_formatted} | 🔢 {scene['total_count']}\n"
            f"   👉  {seg.episode_title}"
        )

    lines = [_scene_line(i + 1, scene) for i, scene in enumerate(scenes[:_PREVIEW_COUNT])]
    count_emoji = convert_number_to_emoji(len(scenes))

    header = f"🎯 *Obiekt: {class_name}* 🎯\n"
    if qty_filter_str:
        header += f"🔢 *Filtr: {qty_filter_str}* 🔢\n"
    header += f"👁️ *Znaleziono:* {count_emoji} scen 👁️\n\n"

    hint = f"\n\n\n👉 Z filtrem: /obj {class_name} =N lub /obj {class_name} >N"
    code_header = f"Obiekt:\u00A0{class_name}".replace(" ", "\u00A0")
    return header + f"```{code_header}\n\n" + "\n\n".join(lines) + hint + "\n```"


def get_no_objects_message() -> str:
    return BotResponse.warning("BRAK DANYCH", "Brak obiektów w bazie danych.")


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
