from bot.responses.bot_response import BotResponse


def get_usage_message() -> str:
    return BotResponse.usage(
        command="zapiszn",
        error_title="BRAK ARGUMENTÓW",
        usage_syntax="<numer> [left_adjust] [right_adjust] <nazwa>",
        params=[
            ("<numer>", "numer segmentu z wyników /szukaj (1-based)"),
            ("<left_adjust>", "sekundy: ujemne = przytnij, dodatnie = wydłuż (opcjonalny)"),
            ("<right_adjust>", "sekundy: ujemne = przytnij, dodatnie = wydłuż (opcjonalny)"),
            ("<nazwa>", "nazwa klipu (tylko litery, cyfry, podkreślnik; max 50 znaków)"),
        ],
        example="/zapiszn 3 śmieszny  LUB  /zapiszn 3 -2 1.5 śmieszny",
    )


def get_no_previous_search_message() -> str:
    return BotResponse.warning("BRAK POPRZEDNICH WYNIKÓW", "Najpierw wykonaj wyszukiwanie za pomocą /szukaj")


def get_invalid_segment_number_message(segment_number: int) -> str:
    return BotResponse.error("NIEPRAWIDŁOWY NUMER SEGMENTU", f"Segment nr {segment_number} nie istnieje w wynikach")


def get_invalid_adjust_format_message() -> str:
    return BotResponse.error("NIEPRAWIDŁOWY ADJUST", "Wartości adjust muszą być liczbami. Podaj oba (left right) lub żaden")


def get_clip_name_numeric_message() -> str:
    return BotResponse.error("NIEPRAWIDŁOWA NAZWA KLIPU", "Nazwa nie może składać się wyłącznie z cyfr")


def get_clip_name_length_exceeded_message() -> str:
    return BotResponse.error("NAZWA ZA DŁUGA", "Przekroczono limit długości nazwy klipu")


def get_clip_name_exists_message(clip_name: str) -> str:
    return BotResponse.warning("NAZWA KLIPU ZAJĘTA", f"Klip o nazwie '{clip_name}' już istnieje. Wybierz inną nazwę")


def get_clip_limit_exceeded_message() -> str:
    return BotResponse.error("LIMIT ZAPISANYCH KLIPÓW", "Usuń stare klipy, aby zapisać nowy")


def get_clip_saved_successfully_message(clip_name: str) -> str:
    return BotResponse.success("KLIP ZAPISANY", f"Klip '{clip_name}' został zapisany pomyślnie")


def get_log_no_previous_search_message() -> str:
    return "No previous search results found for user."


def get_log_invalid_segment_number_message(segment_number: int) -> str:
    return f"Invalid segment number provided: {segment_number}"


def get_log_invalid_adjust_format_message() -> str:
    return "Invalid adjust format provided for save by index."


def get_log_clip_name_numeric_message(clip_name: str, username: str) -> str:
    return f"Clip name '{clip_name}' consists only of digits for user '{username}'. Not allowed."


def get_log_clip_name_exists_message(clip_name: str, username: str) -> str:
    return f"Clip name '{clip_name}' already exists for user '{username}'."


def get_log_clip_saved_successfully_message(clip_name: str, username: str) -> str:
    return f"Clip '{clip_name}' saved successfully (by index) for user '{username}'."
