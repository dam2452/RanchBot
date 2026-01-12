from pathlib import Path
from typing import List

from bot.database.models import UserProfile


def get_general_error_message() -> str:
    return "⚠️ Wystąpił błąd podczas przetwarzania żądania. Prosimy spróbować ponownie później.⚠️"


def get_invalid_args_count_message(action_name: str, user_id: int) -> str:
    return f"Incorrect command ({action_name}) format provided by user '{user_id}'."


def format_user(user: UserProfile) -> str:
    return (
        f"👤 ID: {user.user_id}\n"
        f"👤 Username: {user.username or 'N/A'}\n"
        f"📛 Full Name: {user.full_name or 'N/A'}\n"
        f"🔒 Subscription End: {user.subscription_end or 'N/A'}\n"
        f"📝 Note: {user.note or 'N/A'}\n"
    )


def get_users_string(users: List[UserProfile]) -> str:
    return "\n".join([format_user(user) for user in users]) + "\n"


def get_no_segments_found_message(quote: str) -> str:
    return f"❌ Nie znaleziono pasujących cytatów dla: '{quote}'.❌"


def get_log_no_segments_found_message(quote: str) -> str:
    return f"No segments found for quote: '{quote}'"


def get_extraction_failure_message() -> str:
    return "⚠️ Nie udało się wyodrębnić klipu wideo.⚠️"


def get_log_extraction_failure_message(exception: Exception) -> str:
    return f"Failed to extract video clip: {exception}"


def get_limit_exceeded_message() -> str:
    return "❌ Przekroczono limit wiadomości. Spróbuj ponownie później.❌"


def get_message_too_long_message() -> str:
    return "❌ Wiadomość jest zbyt długa.❌"

def get_log_clip_duration_exceeded_message(user_id: int) -> str:
    return f"Clip duration limit exceeded for user '{user_id}'"

def get_clip_size_log_message(file_path: Path, file_size: float) -> str:
    return f"{file_path} Rozmiar klipu: {file_size:.2f} MB"


def get_clip_size_exceed_log_message(file_size: float, limit_size: float) -> str:
    return f"Rozmiar klipu {file_size:.2f} MB przekracza limit {limit_size} MB."


def get_clip_size_exceed_message() -> str:
    return "❌ Wyodrębniony klip jest za duży, aby go wysłać przez Telegram. Maksymalny rozmiar pliku to 50 MB.❌"


def get_video_sent_log_message(file_path: Path) -> str:
    return f"Wysłano plik wideo: {file_path}"
