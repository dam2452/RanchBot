from datetime import date

from bot.responses.bot_response import BotResponse


def get_invalid_args_message() -> str:
    return BotResponse.usage(
        command="addsub",
        error_title="BRAK ARGUMENTÓW",
        usage_syntax="<user_id> <dni>",
        params=[
            ("<user_id>", "ID użytkownika Telegram"),
            ("<dni>", "liczba dni subskrypcji"),
        ],
        example="/addsub 123456789 30",
    )


def get_subscription_extended_message(username: str, new_end_date: date) -> str:
    return BotResponse.success("SUBSKRYPCJA PRZEDŁUŻONA", f"Subskrypcja dla użytkownika {username} przedłużona do {new_end_date}")


def get_subscription_error_message() -> str:
    return BotResponse.error("BŁĄD SUBSKRYPCJI", "Wystąpił błąd podczas przedłużania subskrypcji")


def get_subscription_log_message(username: str, executor: str) -> str:
    return f"Subscription for user {username} extended by {executor}."


def get_subscription_error_log_message() -> str:
    return "An error occurred while extending the subscription."
