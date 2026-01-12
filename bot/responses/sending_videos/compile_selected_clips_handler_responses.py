def get_invalid_args_count_message() -> str:
    return "📄 Podaj numery klipów do skompilowania w odpowiedniej kolejności."


def get_no_matching_clips_found_message() -> str:
    return "❌ Nie znaleziono pasujących klipów do kompilacji."


def get_clip_not_found_message(clip_number: int) -> str:
    return f"❌ Nie znaleziono klipu o numerze '{clip_number}'."


def get_log_no_matching_clips_found_message() -> str:
    return "No matching clips found for compilation."


def get_log_clip_not_found_message(clip_name: str, username: str) -> str:
    return f"Clip '{clip_name}' not found for user '{username}'."


def get_compiled_clip_sent_message(username: str) -> str:
    return f"Compiled clip sent to user '{username}' and temporary files removed."


def get_max_clips_exceeded_message() -> str:
    return "❌ Przekroczono maksymalną liczbę klipów do skompilowania.❌"


def get_clip_time_message() -> str:
    return "❌ Przekroczono maksymalny czas trwania kompilacji.❌"
