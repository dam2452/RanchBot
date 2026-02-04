def get_serial_usage_message() -> str:
    return "❌ Podaj nazwę serialu. Przykład: /serial kiepscy ❌"


def get_serial_changed_message(series_name: str) -> str:
    return f"✅ Zmieniono aktywny serial na: {series_name} ✅"


def get_serial_invalid_message(series_name: str, available: list) -> str:
    series_list = ", ".join(available) if available else "brak"
    return f"❌ Nieznany serial: {series_name}\n\nDostępne: {series_list} ❌"


def get_serial_current_message(series_name: str, available_series: list = None) -> str:
    if available_series is None:
        return f"📺 Twój aktywny serial: {series_name}"

    current_info = f"📺 Aktualny: {series_name}" if series_name else "📺 Aktualny: brak (ustaw serial używając /serial <nazwa>)"

    series_list = "\n".join([f"   • {s}" for s in available_series]) if available_series else "   • brak dostępnych seriali"

    return f"""```
═══════════════════════════
📺 WYBÓR SERIALU 📺
═══════════════════════════
{current_info}

📋 Dostępne seriale:
{series_list}

💡 Użycie:
   /serial <nazwa>

Przykład: /serial ranczo
═══════════════════════════
```"""
