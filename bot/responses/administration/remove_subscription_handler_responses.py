def get_no_username_provided_message() -> str:
    return "✏️ Podaj nazwę użytkownika.✏️"


def get_subscription_removed_message(username: str) -> str:
    return f"✅ Subskrypcja dla użytkownika {username} została usunięta.✅"


def get_log_subscription_removed_message(username: str, removed_by: str) -> str:
    return f"Subscription for user {username} removed by {removed_by}."

def get_no_user_id_provided_message() -> str:
    return "⚠️ Nie podano ID użytkownika.⚠️"
