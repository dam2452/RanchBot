from typing import (
    Any,
    Dict,
    List,
)

from bot.utils.functions import (
    convert_number_to_emoji,
    format_segment,
)


def format_search_filter_response(total_count: int, segments: List[Dict[str, Any]]) -> str:
    emoji_count = convert_number_to_emoji(total_count)
    response = (
        f"🔎 *Wyniki filtra* 🔎\n"
        f"👁️ *Znaleziono:* {emoji_count} scen pasujących do aktywnego filtra 👁️\n\n"
    )
    segment_lines = []
    for i, segment in enumerate(segments[:5], start=1):
        info = format_segment(segment)
        segment_lines.append(
            f"{convert_number_to_emoji(i)}  | 📺 {info.episode_formatted} | 🕒 {info.time_formatted}\n"
            f"   👉  {info.episode_title}",
        )
    response += "```Filtr aktywny\n".replace(" ", "\u00A0") + "\n\n".join(segment_lines) + "\n```"
    return response


def get_log_search_filter_results_sent_message(username: str, count: int) -> str:
    return f"Search-by-filter results ({count}) sent to user '{username}'."


def get_log_search_filter_no_results_message(chat_id: int) -> str:
    return f"Search-by-filter: no segments matched filter for chat_id={chat_id}."
