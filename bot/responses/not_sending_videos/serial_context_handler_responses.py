from typing import (
    List,
    Optional,
)

from bot.responses.bot_response import BotResponse


def __fmt(series_name: str) -> str:
    return series_name.replace("_", " ").title()


def get_serial_changed_message(series_name: str) -> str:
    return BotResponse.success("SERIAL ZMIENIONY", f"Zmieniono aktywny serial na: {__fmt(series_name)}")


def get_serial_invalid_message(series_name: str, available: List[str]) -> str:
    series_list = ", ".join([__fmt(s) for s in available]) if available else "brak"
    return BotResponse.error("NIEZNANY SERIAL", f"Nieznany serial: {__fmt(series_name)}\n\nDostępne: {series_list}")


def get_serial_current_message(series_name: str, available_series: Optional[List[str]] = None) -> str:
    if available_series is None:
        return BotResponse.info("AKTYWNY SERIAL", f"Twój aktywny serial: {__fmt(series_name)}")

    series_list = "\n".join([
        f"💥 {__fmt(s)} 💥" if s == series_name else f"• {__fmt(s)}"
        for s in available_series
    ]) if available_series else "• brak dostępnych seriali"

    body = (
        f"📋 Dostępne seriale:\n\n"
        f"{series_list}\n\n"
        f"💡 Użycie:\n"
        f"   /serial <nazwa>\n\n"
        f"Przykład: /serial ranczo"
    )
    return BotResponse.info("WYBÓR SERIALU", body)


def get_no_series_name_provided_message() -> str:
    return BotResponse.usage(
        command="serial",
        error_title="BRAK NAZWY SERIALU",
        usage_syntax="<nazwa_serialu>",
        params=[("<nazwa_serialu>", "nazwa serialu (np. ranczo, kiepscy)")],
        example="/serial ranczo",
    )
