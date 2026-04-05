from bot.responses.bot_response import BotResponse


def get_no_last_clip_message() -> str:
    return BotResponse.error("BRAK KLIPU", "Najpierw wyszukaj klip, a potem użyj /tiktak")


def get_tiktak_success_log(username: str) -> str:
    return f"TikTak clip generated for user '{username}'"


def get_tiktak_compiled_note() -> str:
    return BotResponse.warning(
        "KOMPILACJA",
        "Dla kompilacji zastosowano statyczne kadrowanie centralne (brak danych detekcji).",
    )


def get_tiktak_no_detections_note() -> str:
    return BotResponse.warning(
        "BRAK DETEKCJI",
        "Nie znaleziono danych o osobach - zastosowano kadrowanie centralne.",
    )
