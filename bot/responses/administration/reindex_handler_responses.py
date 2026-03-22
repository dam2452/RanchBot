from typing import List

from aiogram.utils.markdown import markdown_decoration

from bot.responses.bot_response import BotResponse


def get_delete_started_message(series_name: str) -> str:
    return BotResponse.info("USUWANIE SERIALU", f"Usuwam indeksy dla: {series_name}")


def get_delete_complete_message(series_name: str, deleted: List[str]) -> str:
    if deleted:
        body = f"Serial: {series_name}\nUsuniete indeksy ({len(deleted)}):\n" + "\n".join(f"- {i}" for i in deleted)
    else:
        body = f"Serial: {series_name}\nBrak indeksow do usuniecia."
    return BotResponse.success("SERIAL USUNIETY", body)


def get_reindex_started_message(target: str) -> str:
    return BotResponse.info("REINDEKSOWANIE ROZPOCZĘTE", f"Rozpoczynam reindeksowanie: {target}")


def get_reindex_progress_message(message: str, current: int, total: int) -> str:
    safe_message = markdown_decoration.quote(message)

    if total == 0:
        return f"🔄 {safe_message}"

    percentage = int((current / total) * 100)
    bar_length = 10
    filled = int((percentage / 100) * bar_length)

    progress_bar = "🟩" * filled + "⬜" * (bar_length - filled)

    return (
        f"🔄 *Reindeksowanie w toku*\n\n"
        f"📝 {safe_message}\n\n"
        f"{progress_bar}\n\n"
        f"📊 Postęp: *{percentage}%*"
    )


def get_reindex_complete_message(result) -> str:
    body = (
        f"Serial: {result.series_name}\n"
        f"Odcinki: {result.episodes_processed}\n"
        f"Dokumenty: {result.documents_indexed}"
    )
    if result.errors:
        error_list = "\n".join(f"- {err}" for err in result.errors[:3])
        body += f"\n\nBledy ({len(result.errors)}):\n{error_list}"
        if len(result.errors) > 3:
            body += f"\n... i {len(result.errors) - 3} wiecej"
    return BotResponse.success("REINDEKSOWANIE ZAKONCZONE", body)


def get_reindex_error_message(error: str) -> str:
    return BotResponse.error("BLAD REINDEKSOWANIA", error)


def get_reindex_all_complete_message(series_count: int, episodes: int, documents: int) -> str:
    return BotResponse.success(
        "REINDEKSOWANIE ZAKONCZONE",
        f"Seriale: {series_count}\nOdcinki: {episodes}\nDokumenty: {documents}",
    )


def get_reindex_all_new_complete_message(series_count: int, episodes: int, documents: int) -> str:
    return BotResponse.success(
        "NOWE SERIALE ZREINDEKSOWANE",
        f"Nowe seriale: {series_count}\nOdcinki: {episodes}\nDokumenty: {documents}",
    )


def get_no_new_series_message() -> str:
    return BotResponse.info("BRAK NOWYCH SERIALI", "Brak nowych seriali do reindeksowania")


def get_no_target_provided_message() -> str:
    return BotResponse.usage(
        command="reindex",
        error_title="BRAK CELU",
        usage_syntax="<all | all-new | delete <nazwa> | nazwa_serialu>",
        params=[
            ("all", "reindeksuj wszystkie seriale"),
            ("all-new", "reindeksuj tylko nowe seriale"),
            ("delete <nazwa>", "usun indeksy serialu z Elasticsearch"),
            ("<nazwa>", "reindeksuj konkretny serial np. ranczo"),
        ],
        example="/reindex ranczo  lub  /reindex delete sejm_demo",
    )
