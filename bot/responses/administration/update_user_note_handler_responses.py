from bot.responses.bot_response import BotResponse


def get_no_note_provided_message() -> str:
    return BotResponse.usage(
        command="note",
        error_title="BRAK ARGUMENTÓW",
        usage_syntax="<user_id> <treść_notatki>",
        params=[
            ("<user_id>", "ID użytkownika Telegram"),
            ("<treść_notatki>", "treść notatki (może zawierać spacje)"),
        ],
        example="/note 123456789 Użytkownik premium",
    )


def get_note_updated_message() -> str:
    return BotResponse.success("NOTATKA ZAKTUALIZOWANA", "Notatka została zaktualizowana")


def get_invalid_user_id_message(user_id_str: str) -> str:
    return BotResponse.error("NIEPRAWIDŁOWE ID UŻYTKOWNIKA", f"Nieprawidłowe ID użytkownika: {user_id_str}")


def get_log_note_updated_message(username: str, user_id: int, note: str) -> str:
    return f"Notatka zaktualizowana przez '{username}' dla użytkownika ID {user_id}: {note}"


def get_log_no_note_provided_message(username: str) -> str:
    return f"Nie podano ID użytkownika lub treści notatki przez '{username}'."


def get_log_invalid_user_id_message(username: str, user_id_str: str) -> str:
    return f"Nieprawidłowe ID użytkownika podane przez '{username}': {user_id_str}"
