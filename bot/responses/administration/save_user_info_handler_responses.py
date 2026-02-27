from bot.responses.bot_response import BotResponse


def get_no_message_provided_message() -> str:
    return BotResponse.warning("BRAK WIADOMOŚCI", "Nie podano wiadomości")


def get_message_saved_confirmation() -> str:
    return BotResponse.success("WIADOMOŚĆ ZAPISANA", "Twoja wiadomość została zapisana")


def get_log_message_saved(user_id: int) -> str:
    return f"Message from user {user_id} saved."
