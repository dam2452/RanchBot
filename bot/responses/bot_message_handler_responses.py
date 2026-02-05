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


def get_telegram_clip_too_large_message(clip_duration: float) -> str:
    return (
        f"❌ Klip jest za duży do wysłania ({clip_duration:.1f}s).\n\n"
        f"Telegram ma limit 50MB dla wideo. Spróbuj wybrać krótszy fragment."
    )


def get_log_clip_too_large_message(clip_duration: float, username: str) -> str:
    return f"Clip too large to send via Telegram: {clip_duration:.1f}s for user {username}"


def get_telegram_compilation_too_large_message(total_duration: float) -> str:
    return (
        f"❌ Kompilacja jest za duża do wysłania ({total_duration:.1f}s).\n\n"
        f"Telegram ma limit 50MB dla wideo. Spróbuj:\n"
        f"• Wybrać mniej klipów\n"
        f"• Wybrać krótsze fragmenty"
    )


def get_log_compilation_too_large_message(total_duration: float, username: str) -> str:
    return f"Compilation too large to send via Telegram: {total_duration:.1f}s for user {username}"


class CustomError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class MessageNotFoundError(CustomError):
    def __init__(self, key: str, handler_name: str, specialized_table: str):
        message = (
            f"Message not found. key='{key}', handler_name='{handler_name}', "
            f"specialized_table='{specialized_table}'"
        )
        super().__init__(message)


class MessageArgumentMismatchError(CustomError):
    def __init__(self, key: str, handler_name: str, expected_count: int, actual_count: int, message_template: str):
        message = (
            f"Argument count mismatch for key='{key}', handler_name='{handler_name}'. "
            f"Expected {expected_count}, got {actual_count}. Template: {message_template}"
        )
        super().__init__(message)


class MessageFormattingError(CustomError):
    def __init__(self, key: str, handler_name: str, message_template: str, args: List[str], error: Exception):
        formatted_args = ', '.join(args) if args else "None"
        message = (
            f"Formatting error for key='{key}', handler_name='{handler_name}'. "
            f"Template: {message_template}, Args: [{formatted_args}], Error: {error}"
        )
        super().__init__(message)
