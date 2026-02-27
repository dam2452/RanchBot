from bot.responses.bot_response import BotResponse


def get_invalid_range_message(index: str) -> str:
    return BotResponse.error("NIEPRAWIDŁOWY ZAKRES", f"Podano nieprawidłowy zakres cytatów: {index}")


def get_invalid_index_message(index: str) -> str:
    return BotResponse.error("NIEPRAWIDŁOWY INDEKS", f"Podano nieprawidłowy indeks cytatu: {index}")


def get_no_previous_search_results_message() -> str:
    return BotResponse.warning("BRAK POPRZEDNICH WYNIKÓW", "Najpierw wykonaj wyszukiwanie za pomocą /szukaj")


def get_no_matching_segments_found_message() -> str:
    return BotResponse.error("BRAK PASUJĄCYCH CYTATÓW", "Nie znaleziono pasujących cytatów do kompilacji")


def get_log_invalid_range_message() -> str:
    return "Invalid range provided."


def get_log_invalid_index_message() -> str:
    return "Invalid index provided."


def get_log_compilation_success_message(username: str) -> str:
    return f"Compiled clip sent to user '{username}' and temporary files removed."


def get_log_no_previous_search_results_message() -> str:
    return "No previous search results found for user."


def get_log_no_matching_segments_found_message() -> str:
    return "No matching segments found for compilation."


def get_log_compiled_clip_is_too_long_message(username: str) -> str:
    return f"Compiled clip is too long for user '{username}'."


def get_max_clips_exceeded_message() -> str:
    return BotResponse.error("LIMIT KLIPÓW", "Przekroczono maksymalną liczbę klipów do skompilowania")


def get_clip_time_message() -> str:
    return BotResponse.error("LIMIT CZASU KOMPILACJI", "Przekroczono maksymalny czas trwania kompilacji")


def get_no_args_provided_message() -> str:
    return BotResponse.usage(
        command="kompiluj",
        error_title="BRAK ARGUMENTÓW",
        usage_syntax="<wszystko | zakres | numery>",
        params=[
            ("wszystko", "kompilacja wszystkich klipów z listy"),
            ("<zakres>", "zakres np. 1-4 (klipy od 1 do 4)"),
            ("<numery>", "wybrane numery np. 1 3 5"),
        ],
        example="/kompiluj 1-4",
    )


def get_selected_clip_message(video_path: str, start: float, end: float, duration: float) -> str:
    return f"Selected clip: {video_path} from {start} to {end} with duration {duration}"
