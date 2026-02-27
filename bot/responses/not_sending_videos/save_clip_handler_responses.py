from bot.responses.bot_response import BotResponse


def get_clip_name_not_provided_message() -> str:
    return BotResponse.usage(
        command="zapisz",
        error_title="BRAK NAZWY KLIPU",
        usage_syntax="<nazwa>",
        params=[("<nazwa>", "nazwa klipu (tylko litery, cyfry, podkreślnik; max 50 znaków)")],
        example="/zapisz traktor",
    )


def get_clip_name_exists_message(clip_name: str) -> str:
    return BotResponse.warning("NAZWA KLIPU ZAJĘTA", f"Klip o nazwie '{clip_name}' już istnieje. Wybierz inną nazwę")


def get_no_segment_selected_message() -> str:
    return BotResponse.warning("BRAK WYBRANEGO SEGMENTU", "Najpierw wybierz segment: /klip, /wytnij lub /wybierz")


def get_failed_to_verify_clip_length_message() -> str:
    return BotResponse.error("BŁĄD WERYFIKACJI DŁUGOŚCI", "Nie udało się zweryfikować długości klipu")


def get_clip_saved_successfully_message(clip_name: str) -> str:
    return BotResponse.success("KLIP ZAPISANY", f"Klip '{clip_name}' został zapisany pomyślnie")


def get_log_clip_name_exists_message(clip_name: str, username: str) -> str:
    return f"Clip name '{clip_name}' already exists for user '{username}'."


def get_log_no_segment_selected_message() -> str:
    return "No segment selected, manual clip, or compiled clip available for user."


def get_log_failed_to_verify_clip_length_message(clip_name: str, username: str) -> str:
    return f"Failed to verify the length of the clip '{clip_name}' for user '{username}'."


def get_log_clip_saved_successfully_message(clip_name: str, username: str) -> str:
    return f"Clip '{clip_name}' saved successfully for user '{username}'."


def get_clip_name_numeric_provided_message() -> str:
    return BotResponse.error("NIEPRAWIDŁOWA NAZWA KLIPU", "Nazwa nie może składać się wyłącznie z cyfr")


def get_clip_name_length_exceeded_message() -> str:
    return BotResponse.error("NAZWA ZA DŁUGA", "Przekroczono limit długości nazwy klipu")


def get_clip_limit_exceeded_message() -> str:
    return BotResponse.error("LIMIT ZAPISANYCH KLIPÓW", "Usuń stare klipy, aby zapisać nowy")


def get_log_clip_name_numeric_message(clip_name: str, username: str) -> str:
    return f"Clip name '{clip_name}' consists only of digits for user '{username}'. Not allowed."
