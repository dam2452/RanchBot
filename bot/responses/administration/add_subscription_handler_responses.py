from datetime import date


def get_no_user_id_provided_message() -> str:
    return "⚠️ Nie podano ID użytkownika ani ilości dni.⚠️"


def get_subscription_extended_message(username: str, new_end_date: date) -> str:
    return f"✅ Subskrypcja dla użytkownika {username} przedłużona do {new_end_date}.✅"


def get_subscription_error_message() -> str:
    return "⚠️ Wystąpił błąd podczas przedłużania subskrypcji.⚠️"


def get_subscription_log_message(username: str, executor: str) -> str:
    return f"Subscription for user {username} extended by {executor}."


def get_subscription_error_log_message() -> str:
    return "An error occurred while extending the subscription."
