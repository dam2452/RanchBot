from bot.responses.bot_response import BotResponse


def get_subscription_removed_message(username: str) -> str:
    return BotResponse.success("SUBSKRYPCJA USUNIĘTA", f"Subskrypcja dla użytkownika {username} została usunięta")


def get_log_subscription_removed_message(username: str, removed_by: str) -> str:
    return f"Subscription for user {username} removed by {removed_by}."


def get_invalid_args_message() -> str:
    return BotResponse.usage(
        command="rmsub",
        error_title="BRAK ID UŻYTKOWNIKA",
        usage_syntax="<user_id>",
        params=[("<user_id>", "ID użytkownika Telegram")],
        example="/rmsub 123456789",
    )
