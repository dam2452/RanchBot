from bot.responses.bot_response import BotResponse


def get_no_clip_identifier_provided_message() -> str:
    return BotResponse.usage(
        command="klatkaklipu",
        error_title="BRAK IDENTYFIKATORA KLIPU",
        usage_syntax="<nazwa_lub_numer> [selektor_klatki]",
        params=[
            ("<nazwa_lub_numer>", "nazwa klipu lub numer z listy /mojeklipy"),
            ("[selektor_klatki]", "p/pierwsza=pierwsza, o/ostatnia=ostatnia, liczba=indeks (domyślnie 0)"),
        ],
        example="/klatkaklipu mojklip p",
    )


def get_clip_not_found_message(identifier: str) -> str:
    return BotResponse.error("KLIP NIE ZNALEZIONY", f"Nie znaleziono klipu '{identifier}'")


def get_invalid_frame_selector_message() -> str:
    return BotResponse.error(
        "NIEPRAWIDŁOWY SELEKTOR",
        "Selektor klatki musi być: p/pierwsza, o/ostatnia lub liczba całkowita",
    )


def get_log_keyframe_sent_message(identifier: str, username: str) -> str:
    return f"Keyframe from saved clip '{identifier}' sent to user '{username}'."


def get_log_clip_not_found_message(identifier: str, username: str) -> str:
    return f"Saved clip '{identifier}' not found for user '{username}'."
