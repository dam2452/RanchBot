def get_no_previous_searches_message() -> str:
    return "🔍 Najpierw wykonaj wyszukiwanie za pomocą /szukaj."


def get_no_previous_searches_log() -> str:
    return "No previous search results found for user."


def get_no_quotes_selected_message() -> str:
    return "⚠️ Najpierw wybierz cytat za pomocą /klip.⚠️"


def get_no_quotes_selected_log() -> str:
    return "No segment selected by user."


def get_invalid_args_count_message() -> str:
    return "📝 Podaj czas w formacie `<float> <float>` lub `<index> <float> <float>`. Przykład: /dostosuj 10.5 -15.2 lub /dostosuj 1 10.5 -15.2"


def get_invalid_args_count_log() -> str:
    return "Invalid number of arguments provided by user."


def get_invalid_interval_message() -> str:
    return "⚠️ Czas zakończenia musi być późniejszy niż czas rozpoczęcia.⚠️"


def get_invalid_interval_log() -> str:
    return "End time must be later than start time."


def get_invalid_segment_index_message() -> str:
    return "⚠️ Podano nieprawidłowy indeks cytatu.⚠️"


def get_invalid_segment_log() -> str:
    return "Invalid segment index provided by user."


def get_extraction_failure_message(exception: Exception) -> str:
    return f"⚠️ Nie udało się zmienić klipu wideo: {exception}"


def get_extraction_failure_log(exception: Exception) -> str:
    return f"Failed to adjust video clip: {exception}"


def get_updated_segment_info_log(chat_id: int) -> str:
    return f"Updated segment info for chat ID '{chat_id}'"


def get_successful_adjustment_message(username: str) -> str:
    return f"Video clip adjusted successfully for user '{username}'."


def get_max_extension_limit_message() -> str:
    return "❌ Przekroczono limit rozszerzenia dla komendy dostosuj. ❌"


def get_max_clip_duration_message() -> str:
    return "❌ Przekroczono maksymalny czas trwania klipu.❌"
