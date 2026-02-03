def get_serial_usage_message() -> str:
    return "❌ Podaj nazwę serialu. Przykład: /serial kiepscy ❌"


def get_serial_changed_message(series_name: str) -> str:
    return f"✅ Zmieniono aktywny serial na: {series_name} ✅"


def get_serial_invalid_message(series_name: str, available: list) -> str:
    series_list = ", ".join(available) if available else "brak"
    return f"❌ Nieznany serial: {series_name}\n\nDostępne: {series_list} ❌"


def get_serial_current_message(series_name: str) -> str:
    return f"📺 Twój aktywny serial: {series_name}"
