def get_reindex_usage_message() -> str:
    return """```❌ BŁĄD - BRAK CELU

📋 Podaj cel reindeksowania:
• all - wszystkie seriale
• all-new - tylko nowe seriale
• <nazwa> - konkretny serial

💡 Przykład:
   /reindex ranczo
```"""


def get_reindex_started_message(target: str) -> str:
    return f"🔄 Rozpoczynam reindeksowanie: {target}"


def get_reindex_progress_message(message: str, current: int, total: int) -> str:
    if total == 0:
        return f"🔄 {message}"

    percentage = int((current / total) * 100)
    bar_length = 10
    filled = int((percentage / 100) * bar_length)

    progress_bar = "🟩" * filled + "⬜" * (bar_length - filled)

    return (
        f"🔄 *Reindeksowanie w toku*\n\n"
        f"📝 {message}\n\n"
        f"{progress_bar}\n\n"
        f"📊 Postęp: *{percentage}%*"
    )


def get_reindex_complete_message(result) -> str:
    error_info = ""
    if result.errors:
        error_list = "\n".join(f"- {err}" for err in result.errors[:3])
        error_info = f"\n\n⚠️ Błędy ({len(result.errors)}):\n```\n{error_list}\n```"
        if len(result.errors) > 3:
            error_info += f"\n... i {len(result.errors) - 3} więcej"

    return (
        f"✅ Reindeksowanie zakończone!\n\n"
        f"Serial: {result.series_name}\n"
        f"Odcinki: {result.episodes_processed}\n"
        f"Dokumenty: {result.documents_indexed}"
        f"{error_info}"
    )


def get_reindex_error_message(error: str) -> str:
    return f"❌ Błąd reindeksowania:\n```\n{error}\n```"


def get_reindex_all_complete_message(series_count: int, episodes: int, documents: int) -> str:
    return (
        f"✅ Reindeksowanie wszystkich seriali zakończone!\n\n"
        f"Seriale: {series_count}\n"
        f"Odcinki: {episodes}\n"
        f"Dokumenty: {documents}"
    )


def get_reindex_all_new_complete_message(series_count: int, episodes: int, documents: int) -> str:
    return (
        f"✅ Reindeksowanie nowych seriali zakończone!\n\n"
        f"Nowe seriale: {series_count}\n"
        f"Odcinki: {episodes}\n"
        f"Dokumenty: {documents}"
    )


def get_no_new_series_message() -> str:
    return "📺 Brak nowych seriali do reindeksowania."
