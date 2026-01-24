def get_invalid_args_count_message() -> str:
    return "📋 Podaj numer cytatu, który chcesz wybrać. Przykład: /wybierz 1"


def get_no_previous_search_message() -> str:
    return "🔍 Najpierw wykonaj wyszukiwanie za pomocą /szukaj."


def get_invalid_segment_number_message() -> str:
    return "❌ Nieprawidłowy numer cytatu.❌"


def get_log_no_previous_search_message() -> str:
    return "No previous search results found for user."


def get_log_invalid_segment_number_message(segment_number: int) -> str:
    return f"Invalid segment number provided by user: {segment_number}"


def get_log_segment_selected_message(segment_id: str, username: str) -> str:
    return f"Segment {segment_id} selected by user '{username}'."


def get_limit_exceeded_clip_duration_message() -> str:
    return "❌ Przekroczono limit długości klipu.❌"
