from bot.responses.bot_response import BotResponse


def get_no_last_clip_message() -> str:
    return BotResponse.warning("BRAK OSTATNIEGO KLIPU", "Brak ostatniego klipu. Najpierw wykonaj /klip lub /wybierz")


def get_invalid_result_index_message() -> str:
    return BotResponse.error("NIEPRAWIDŁOWY NUMER WYNIKU", "Numer wyniku musi być liczbą >= 1")


def get_invalid_frame_selector_message() -> str:
    return BotResponse.error(
        "NIEPRAWIDŁOWY SELEKTOR KLATKI",
        "Użyj liczby całkowitej (0=pierwsza, -1=ostatnia) lub aliasu: p/pierwsza/first, o/ostatnia/last",
    )


def get_invalid_frame_index_message(max_index: int) -> str:
    return BotResponse.error(
        "NUMER KLATKI POZA ZAKRESEM",
        f"Dostępne klatki: 0–{max_index} (od końca: -1–-{max_index + 1})",
    )


def get_no_frames_for_navigation_message() -> str:
    return BotResponse.warning(
        "BRAK ZAINDEKSOWANYCH KLATEK",
        "Nawigacja między klatkami wymaga zaindeksowanych klatek kluczowych. Użyj /klatka bez drugiego argumentu.",
    )


def get_no_keyframes_provided_message() -> str:
    return BotResponse.usage(
        command="klatka",
        error_title="UŻYCIE",
        usage_syntax="[numer_wyniku] [klatka]",
        params=[
            ("[numer_wyniku]", "numer wyniku z /szukaj (domyślnie 1)"),
            ("[klatka]", "0/p/pierwsza = pierwsza, -1/o/ostatnia = ostatnia, lub indeks (domyślnie 0)"),
        ],
        example="/klatka 2 ostatnia",
    )


def get_log_keyframe_sent_message(result_index: int, seek_time: float, username: str) -> str:
    return f"Keyframe from result #{result_index} at {seek_time:.2f}s sent to user '{username}'."


def get_log_no_last_clip_message() -> str:
    return "No last clip or search found for keyframe request."
