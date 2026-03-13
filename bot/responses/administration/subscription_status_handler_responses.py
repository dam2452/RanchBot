from datetime import date

from bot.responses.bot_response import BotResponse


def format_subscription_status_response(username: str, subscription_end: date, days_remaining: int) -> str:
    body = (
        f"Uzytkownik: {username}\n"
        f"Data zakonczenia: {subscription_end}\n"
        f"Pozostalo dni: {days_remaining}\n\n"
        "Dziekujemy za wsparcie projektu!"
    )
    return BotResponse.success("STATUS SUBSKRYPCJI", body)


def get_no_subscription_message() -> str:
    return BotResponse.warning("BRAK SUBSKRYPCJI", "Nie masz aktywnej subskrypcji")


def get_log_subscription_status_sent_message(username: str) -> str:
    return f"Subscription status sent to user '{username}'."


def get_log_no_active_subscription_message(username: str) -> str:
    return f"No active subscription found for user '{username}'."
