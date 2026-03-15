from bot.responses.bot_response import BotResponse


def get_no_quote_provided_message() -> str:
    return BotResponse.usage(
        command="kp",
        error_title="BRAK POSTACI",
        usage_syntax="<postać> [emocja]",
        params=[
            ("<postać>", "nazwa postaci (fuzzy, wymagana)"),
            ("[emocja]", "emocja po polsku lub angielsku (opcjonalna)"),
        ],
        example="/kp Michałowa radosny",
    )


def get_no_scenes_found_message(character_name: str, emotion_input: str = "") -> str:
    if emotion_input:
        return BotResponse.warning(
            "BRAK WYNIKÓW",
            f"Nie znaleziono scen z postacią '{character_name}' i emocją '{emotion_input}'.",
        )
    return BotResponse.warning("BRAK WYNIKÓW", f"Nie znaleziono scen z postacią '{character_name}'.")


def get_no_video_path_message() -> str:
    return BotResponse.error("BRAK PLIKU", "Nie znaleziono ścieżki do pliku wideo dla tej sceny.")


def get_log_character_clip_message(character: str, username: str) -> str:
    return f"Character clip for '{character}' sent to user {username}."
