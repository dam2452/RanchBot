from bot.responses.bot_response import BotResponse


def get_user_added_message(username: str) -> str:
    return BotResponse.success("UŻYTKOWNIK DODANY", f"Dodano {username} do whitelisty")


def get_log_user_added_message(username: str, executor: str) -> str:
    return f"User {username} added to whitelist by {executor}."


def get_no_user_id_provided_message() -> str:
    return BotResponse.warning("BRAK ID UŻYTKOWNIKA", "Nie podano ID użytkownika")


def get_user_not_found_message() -> str:
    return BotResponse.error("UŻYTKOWNIK NIE ZNALEZIONY", "Nie można znaleźć użytkownika. Upewnij się, że użytkownik rozpoczął rozmowę z botem")


def get_invalid_args_message() -> str:
    return BotResponse.usage(
        command="addwhitelist",
        error_title="BRAK ID UŻYTKOWNIKA",
        usage_syntax="<user_id>",
        params=[("<user_id>", "ID użytkownika Telegram (liczba)")],
        example="/addwhitelist 123456789",
    )
