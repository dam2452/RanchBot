def get_no_segments_found_message() -> str:
    return "❌ Nie znaleziono pasujących cytatów.❌"


def get_no_quote_provided_message() -> str:
    return "🔎 Podaj cytat, który chcesz znaleźć. Przykład: /klip Nie szkoda panu tego pięknego gabinetu?"


def get_log_segment_saved_message(chat_id: int) -> str:
    return f"Segment saved as last selected for chat ID '{chat_id}'"


def get_log_clip_success_message(username: str) -> str:
    return f"Video clip extracted successfully for user '{username}'."


def get_limit_exceeded_clip_duration_message() -> str:
    return "❌ Przekroczono limit długości klipu.❌"


def get_message_too_long_message() -> str:
    return "❌ Wiadomość jest zbyt długa.❌"
