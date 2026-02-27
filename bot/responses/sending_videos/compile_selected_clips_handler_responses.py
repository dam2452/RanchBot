from bot.responses.bot_response import BotResponse


def get_no_matching_clips_found_message() -> str:
    return BotResponse.error("BRAK PASUJĄCYCH KLIPÓW", "Nie znaleziono pasujących klipów do kompilacji")


def get_clip_not_found_message(clip_number: int) -> str:
    return BotResponse.error("KLIP NIE ZNALEZIONY", f"Nie znaleziono klipu o numerze '{clip_number}'")


def get_log_no_matching_clips_found_message() -> str:
    return "No matching clips found for compilation."


def get_log_clip_not_found_message(clip_name: str, username: str) -> str:
    return f"Clip '{clip_name}' not found for user '{username}'."


def get_compiled_clip_sent_message(username: str) -> str:
    return f"Compiled clip sent to user '{username}' and temporary files removed."


def get_max_clips_exceeded_message() -> str:
    return BotResponse.error("LIMIT KLIPÓW", "Przekroczono maksymalną liczbę klipów do skompilowania")


def get_clip_time_message() -> str:
    return BotResponse.error("LIMIT CZASU KOMPILACJI", "Przekroczono maksymalny czas trwania kompilacji")


def get_no_clip_numbers_provided_message() -> str:
    return BotResponse.usage(
        command="polaczklipy",
        error_title="BRAK NUMERÓW KLIPÓW",
        usage_syntax="<numer1> <numer2> ...",
        params=[("<numer>", "numer zapisanego klipu z /mojeklipy (podaj co najmniej 2)")],
        example="/polaczklipy 1 3 5",
    )
