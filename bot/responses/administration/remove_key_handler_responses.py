def get_remove_key_usage_message() -> str:
    return "❌ Podaj klucz, który chcesz usunąć. Przykład: /removekey some_secret_key"


def get_remove_key_success_message(key: str) -> str:
    return f"✅ Klucz `{key}` został usunięty. ✅"


def get_remove_key_failure_message(key: str) -> str:
    return f"❌ Nie znaleziono klucza `{key}`. ❌"
