from datetime import date


def format_subscription_status_response(username: str, subscription_end: date, days_remaining: int) -> str:
    return f"""
    ✨ **Status Twojej subskrypcji** ✨

👤 **Użytkownik:** {username}
📅 **Data zakończenia:** {subscription_end}
⏳ **Pozostało dni:** {days_remaining}

    Dzięki za wsparcie projektu! 🎉
    """


def get_no_subscription_message() -> str:
    return "🚫 Nie masz aktywnej subskrypcji.🚫"


def get_log_subscription_status_sent_message(username: str) -> str:
    return f"Subscription status sent to user '{username}'."


def get_log_no_active_subscription_message(username: str) -> str:
    return f"No active subscription found for user '{username}'."
