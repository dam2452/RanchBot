from typing import Optional

from bot.responses.bot_response import BotResponse


def get_clip_not_found_message(clip_identifier: Optional[int]) -> str:
    if clip_identifier is None:
        return BotResponse.error("KLIP NIE ZNALEZIONY", "Nie znaleziono klipu o podanej nazwie")
    return BotResponse.error("KLIP NIE ZNALEZIONY", f"Nie znaleziono klipu o numerze '{clip_identifier}'")


def get_log_clip_not_found_message(clip_identifier: Optional[int], username: str) -> str:
    if clip_identifier is None:
        return f"No clip found by name for user: {username}"
    return f"No clip found with number {clip_identifier} for user: {username}"


def get_empty_clip_file_message() -> str:
    return BotResponse.error("PUSTY PLIK KLIPU", "Plik klipu jest pusty")


def get_empty_file_error_message() -> str:
    return BotResponse.error("BŁĄD PLIKU", "Wystąpił błąd podczas wysyłania klipu. Plik jest pusty")


def get_log_empty_clip_file_message(clip_name: str, username: str) -> str:
    return f"Clip file is empty for clip '{clip_name}' by user '{username}'."


def get_log_empty_file_error_message(clip_name: str, username: str) -> str:
    return f"File is empty after writing clip '{clip_name}' for user '{username}'."


def get_log_clip_sent_message(clip_name: str, username: str) -> str:
    return f"Clip '{clip_name}' sent to user '{username}' and temporary file removed."


def get_limit_exceeded_clip_duration_message() -> str:
    return BotResponse.error("LIMIT DŁUGOŚCI KLIPU", "Przekroczono limit długości klipu")


def get_no_clip_number_provided_message() -> str:
    return BotResponse.usage(
        command="wyslij",
        error_title="BRAK NUMERU KLIPU",
        usage_syntax="<numer_klipu>",
        params=[("<numer_klipu>", "numer klipu z listy /mojeklipy")],
        example="/wyslij 1",
    )
