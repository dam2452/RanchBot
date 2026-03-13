from bot.responses.bot_response import BotResponse


def get_no_previous_searches_message() -> str:
    return BotResponse.warning("BRAK POPRZEDNICH WYNIKÓW", "Najpierw wykonaj wyszukiwanie /szukaj <cytat>")


def get_no_previous_searches_log() -> str:
    return "No previous search results found for user."


def get_no_quotes_selected_message() -> str:
    return BotResponse.warning("BRAK WYBRANEGO CYTATU", "Najpierw wybierz cytat: /szukaj, następnie /wybierz")


def get_no_quotes_selected_log() -> str:
    return "No segment selected by user."


def get_invalid_interval_message() -> str:
    return BotResponse.error("NIEPRAWIDŁOWY ZAKRES CZASU", "Czas zakończenia musi być późniejszy niż czas rozpoczęcia")


def get_invalid_interval_log() -> str:
    return "End time must be later than start time."


def get_invalid_segment_index_message() -> str:
    return BotResponse.error("NIEPRAWIDŁOWY INDEKS SEGMENTU", "Podany indeks segmentu jest poza zakresem")


def get_invalid_segment_log() -> str:
    return "Invalid segment index provided by user."


def get_extraction_failure_message(exception: Exception) -> str:
    return BotResponse.error("BŁĄD EKSTRAKCJI", f"Nie udało się zmienić klipu wideo: {exception}")


def get_extraction_failure_log(exception: Exception) -> str:
    return f"Failed to adjust video clip: {exception}"


def get_updated_segment_info_log(chat_id: int) -> str:
    return f"Updated segment info for chat ID '{chat_id}'"


def get_successful_adjustment_message(username: str) -> str:
    return f"Video clip adjusted successfully for user '{username}'."


def get_max_extension_limit_message() -> str:
    return BotResponse.error("LIMIT ROZSZERZENIA", "Przekroczono limit rozszerzenia klipu")


def get_max_clip_duration_message() -> str:
    return BotResponse.error("LIMIT DŁUGOŚCI KLIPU", "Przekroczono maksymalną długość klipu")


def get_invalid_args_count_message() -> str:
    return BotResponse.usage(
        command="dostosuj",
        error_title="BRAK ARGUMENTÓW",
        usage_syntax="[numer_klipu] <przed> <po>",
        params=[
            ("[numer_klipu]", "opcjonalny numer klipu z listy /szukaj"),
            ("<przed>", "rozszerzenie startu w sekundach (może być ujemne)"),
            ("<po>", "rozszerzenie końca w sekundach (może być ujemne)"),
        ],
        example="/dostosuj -1.5 2.0",
    )
