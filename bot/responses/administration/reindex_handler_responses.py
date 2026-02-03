def get_reindex_usage_message() -> str:
    return "❌ Podaj cel: all, all-new lub nazwę serialu. Przykład: /reindex ranczo ❌"


def get_reindex_started_message(target: str) -> str:
    return f"🔄 Rozpoczynam reindeksowanie: {target}"


def get_reindex_progress_message(message: str, current: int, total: int) -> str:
    if total == 0:
        return f"🔄 {message}"
    percentage = int((current / total) * 100)
    return f"🔄 {message} ({percentage}%)"


def get_reindex_complete_message(result) -> str:
    error_info = ""
    if result.errors:
        error_info = f"\n\n⚠️ Błędy ({len(result.errors)}):\n" + "\n".join(
            f"- {err}" for err in result.errors[:3]
        )
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
    return f"❌ Błąd reindeksowania:\n{error} ❌"


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
