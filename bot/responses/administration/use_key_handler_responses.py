def get_no_message_provided_message() -> str:
    return "⚠️ Nie podano klucza.⚠️ Przykład: /klucz tajny_klucz"


def get_message_saved_confirmation() -> str:
    return "✅Twoja wiadomość została zapisana.✅"


def get_log_message_saved(user_id: int) -> str:
    return f"Message from user {user_id} saved."


def get_subscription_redeemed_message(days: int) -> str:
    return f"🎉 Subskrypcja przedłużona o {days} dni! 🎉"


def get_invalid_key_message() -> str:
    return "❌ Podany klucz jest niepoprawny lub został już wykorzystany. ❌"
