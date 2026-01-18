def get_invalid_args_count_message() -> str:
    return "❌ Podaj numer klipu do usunięcia. Przykład: /usunklip numer_klipu ❌"


def get_clip_not_exist_message(clip_number: str) -> str:
    return f"🚫 Klip o nazwie '{clip_number}' nie istnieje.🚫"


def get_clip_deleted_message(clip_name: str) -> str:
    return f"✅ Klip o nazwie '{clip_name}' został usunięty.✅"


def get_log_clip_not_exist_message(clip_number: int, username: str) -> str:
    return f"Clip '{clip_number}' does not exist for user '{username}'."


def get_log_clip_deleted_message(clip_name: str, username: str) -> str:
    return f"Clip '{clip_name}' has been successfully deleted for user '{username}'."

def get_log_no_saved_clips_message(username: str) -> str:
    return f"User '{username}' has no clips to delete."
