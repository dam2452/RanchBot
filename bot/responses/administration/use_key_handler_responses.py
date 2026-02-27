from bot.responses.bot_response import BotResponse


def get_no_message_provided_message() -> str:
    return BotResponse.usage(
        command="klucz",
        error_title="BRAK KLUCZA",
        usage_syntax="<klucz_subskrypcyjny>",
        params=[("<klucz_subskrypcyjny>", "klucz subskrypcyjny do aktywacji")],
        example="/klucz tajny_klucz",
    )


def get_message_saved_confirmation() -> str:
    return BotResponse.success("WIADOMOŚĆ ZAPISANA", "Twoja wiadomość została zapisana")


def get_log_message_saved(user_id: int) -> str:
    return f"Message from user {user_id} saved."


def get_subscription_redeemed_message(days: int) -> str:
    return BotResponse.success("SUBSKRYPCJA PRZEDŁUŻONA", f"Subskrypcja przedłużona o {days} dni")


def get_invalid_key_message() -> str:
    return BotResponse.error("NIEPRAWIDŁOWY KLUCZ", "Podany klucz jest niepoprawny lub został już wykorzystany")
