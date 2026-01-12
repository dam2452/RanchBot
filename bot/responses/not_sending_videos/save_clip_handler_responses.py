def get_clip_name_exists_message(clip_name: str) -> str:
    return f"⚠️ Klip o takiej nazwie '{clip_name}' już istnieje. Wybierz inną nazwę.⚠️"


def get_no_segment_selected_message() -> str:
    return "⚠️ Najpierw wybierz segment za pomocą /klip, /wytnij lub skompiluj klipy.⚠️"


def get_failed_to_verify_clip_length_message() -> str:
    return "❌ Nie udało się zweryfikować długości klipu.❌"


def get_clip_saved_successfully_message(clip_name: str) -> str:
    return f"✅ Klip '{clip_name}' został zapisany pomyślnie. ✅"


def get_log_clip_name_exists_message(clip_name: str, username: str) -> str:
    return f"Clip name '{clip_name}' already exists for user '{username}'."


def get_log_no_segment_selected_message() -> str:
    return "No segment selected, manual clip, or compiled clip available for user."


def get_log_failed_to_verify_clip_length_message(clip_name: str, username: str) -> str:
    return f"Failed to verify the length of the clip '{clip_name}' for user '{username}'."


def get_log_clip_saved_successfully_message(clip_name: str, username: str) -> str:
    return f"Clip '{clip_name}' saved successfully for user '{username}'."


def get_clip_name_not_provided_message():
    return "📝 Podaj nazwę klipu. Przykład: /zapisz nazwa_klipu"


def get_clip_name_length_exceeded_message():
    return "❌ Przekroczono limit długości nazwy klipu.❌"


def get_clip_limit_exceeded_message() -> str:
    return "❌ Przekroczono limit zapisanych klipów. Usuń kilka starych, aby móc zapisać nowy. ❌"
