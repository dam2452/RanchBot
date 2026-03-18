from typing import (
    List,
    Optional,
)

from bot.responses.bot_response import BotResponse
from bot.types import SearchFilter


def get_filter_resolution_notes_message(notes: List[str]) -> str:
    body = "\n".join(f"• {n}" for n in notes)
    return BotResponse.info("DOPASOWANIA FILTRÓW", body)


def get_no_args_message() -> str:
    return BotResponse.usage(
        command="filtr",
        error_title="BRAK ARGUMENTÓW",
        usage_syntax="[reset|info|<filtry>]",
        params=[
            ("reset", "usuwa wszystkie aktywne filtry"),
            ("info", "wyświetla aktywne filtry"),
            ("sezon:X", "filtr po sezonie (np. sezon:1, sezon:1-3, sezon:1,3,5)"),
            ("odcinek:X", "filtr po odcinku (np. odcinek:S01E05, odcinek:S01E03-S01E07)"),
            ("tytul:X", "filtr po tytule odcinka (fuzzy match)"),
            ("postac:X", "postać widoczna na scenie (np. postac:Lucy, postac:Lucy,Kusy)"),
            ("emocja:X", "emocja postaci na scenie (np. emocja:radosny, emocja:smutny,neutralny)"),
            ("obiekt:X", "obiekt na scenie (np. obiekt:krzeslo, obiekt:krzeslo>3)"),
        ],
        example="/filtr sezon:2 postac:Kusy emocja:radosny",
    )


def get_filter_set_message(search_filter: SearchFilter) -> str:
    return BotResponse.success("FILTRY USTAWIONE", _format_filter(search_filter))


def get_filter_reset_message() -> str:
    return BotResponse.success("FILTRY ZRESETOWANE", "Wszystkie filtry zostały usunięte.")


def get_filter_info_message(search_filter: Optional[SearchFilter]) -> str:
    if not search_filter:
        return BotResponse.info("AKTYWNE FILTRY", "Brak aktywnych filtrów.")
    return BotResponse.info("AKTYWNE FILTRY", _format_filter(search_filter))


def get_filter_parse_errors_message(errors: List[str]) -> str:
    body = "\n".join(f"• {e}" for e in errors)
    return BotResponse.error("BŁĄD PARSOWANIA FILTRÓW", body)


def get_filter_expired_message() -> str:
    return BotResponse.warning(
        "FILTRY WYGASŁY",
        "Filtry zostały zresetowane po 1h nieaktywności. Wyszukiwanie bez filtrów.",
    )


def get_log_filter_set_message(chat_id: int) -> str:
    return f"Search filters updated for chat_id={chat_id}."


def get_log_filter_reset_message(chat_id: int) -> str:
    return f"Search filters reset for chat_id={chat_id}."


def _format_filter(search_filter: SearchFilter) -> str:
    lines = []
    if search_filter.get("seasons"):
        lines.append(f"Sezony: {', '.join(str(s) for s in search_filter['seasons'])}")
    if search_filter.get("episodes"):
        ep_strs = []
        for ep in search_filter["episodes"]:
            if ep.get("season") is not None:
                ep_strs.append(f"S{ep['season']:02d}E{ep['episode']:02d}")
            else:
                ep_strs.append(f"E{ep['episode']:02d}")
        lines.append(f"Odcinki: {', '.join(ep_strs)}")
    if search_filter.get("episode_title"):
        lines.append(f"Tytuł: {search_filter['episode_title']}")
    if search_filter.get("character_groups"):
        groups = [" LUB ".join(g) for g in search_filter["character_groups"]]
        lines.append(f"Postaci: {' ORAZ '.join(groups)}")
    if search_filter.get("emotions"):
        lines.append(f"Emocje: {' LUB '.join(search_filter['emotions'])}")
    if search_filter.get("object_groups"):
        groups = []
        for group in search_filter["object_groups"]:
            parts = []
            for obj in group:
                if obj.get("operator") and obj.get("value") is not None:
                    parts.append(f"{obj['name']}{obj['operator']}{obj['value']}")
                else:
                    parts.append(obj["name"])
            groups.append(" LUB ".join(parts))
        lines.append(f"Obiekty: {' ORAZ '.join(groups)}")
    return "\n".join(lines) if lines else "Brak aktywnych filtrów."
