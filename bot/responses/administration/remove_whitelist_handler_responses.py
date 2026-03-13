from bot.responses.bot_response import BotResponse


def get_user_removed_message(username: str) -> str:
    return BotResponse.success("UŻYTKOWNIK USUNIĘTY", f"Usunięto {username} z whitelisty")


def get_log_user_removed_message(username: str, removed_by: str) -> str:
    return f"User {username} removed from whitelist by {removed_by}."


def get_user_not_in_whitelist_message(user_id: int) -> str:
    return BotResponse.warning("UŻYTKOWNIK NIE NA WHITELIST", f"Użytkownik {user_id} nie znajduje się na whitelist")


def get_log_user_not_in_whitelist_message(user_id: int) -> str:
    return f"User {user_id} not found in whitelist."


def get_invalid_args_message() -> str:
    return BotResponse.usage(
        command="removewhitelist",
        error_title="BRAK ID UŻYTKOWNIKA",
        usage_syntax="<user_id>",
        params=[("<user_id>", "ID użytkownika Telegram do usunięcia z whitelisty")],
        example="/removewhitelist 123456789",
    )
