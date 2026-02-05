def get_serial_usage_message() -> str:
    return "❌ Podaj nazwę serialu. Przykład: /serial kiepscy ❌"


def get_serial_changed_message(series_name: str) -> str:
    return f"✅ Zmieniono aktywny serial na: {series_name.capitalize()} ✅"


def get_serial_invalid_message(series_name: str, available: list) -> str:
    series_list = ", ".join([s.capitalize() for s in available]) if available else "brak"
    return f"❌ Nieznany serial: {series_name.capitalize()}\n\nDostępne: {series_list} ❌"


def get_serial_current_message(series_name: str, available_series: list = None) -> str:
    if available_series is None:
        return f"📺 Twój aktywny serial: {series_name.capitalize()}"

    series_list = "\n".join([
        f"💥 {s.capitalize()} 💥" if s == series_name else f"• {s.capitalize()}"
        for s in available_series
    ]) if available_series else "• brak dostępnych seriali"

    return (f"""```📺 WYBÓR SERIALU 📺

📋 Dostępne seriale:
{series_list}

💡 Użycie:
   /serial <nazwa>

Przykład: /serial ranczo
```""").replace(" ", "\u00A0")
