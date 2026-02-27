from bot.responses.bot_response import BotResponse


def get_no_previous_search_message() -> str:
    return BotResponse.warning("BRAK POPRZEDNICH WYNIKÓW", "Najpierw wykonaj wyszukiwanie za pomocą /szukaj")


def get_invalid_segment_number_message() -> str:
    return BotResponse.error("NIEPRAWIDŁOWY NUMER CYTATU", "Nieprawidłowy numer cytatu")


def get_log_no_previous_search_message() -> str:
    return "No previous search results found for user."


def get_log_invalid_segment_number_message(segment_number: int) -> str:
    return f"Invalid segment number provided by user: {segment_number}"


def get_log_segment_selected_message(segment_id: str, username: str) -> str:
    return f"Segment {segment_id} selected by user '{username}'."


def get_limit_exceeded_clip_duration_message() -> str:
    return BotResponse.error("LIMIT DŁUGOŚCI KLIPU", "Przekroczono limit długości klipu")


def get_no_clip_number_provided_message() -> str:
    return BotResponse.usage(
        command="wybierz",
        error_title="BRAK NUMERU KLIPU",
        usage_syntax="<numer_klipu>",
        params=[("<numer_klipu>", "numer klipu z wyników /szukaj (1-5)")],
        example="/wybierz 2",
    )
