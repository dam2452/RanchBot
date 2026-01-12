from bot.utils.functions import (
    convert_number_to_emoji,
    format_segment,
)


def get_invalid_args_count_message() -> str:
    return "🔍 Podaj cytat, który chcesz znaleźć. Przykład: /szukaj geniusz"


def format_search_response(unique_segments_count: int, segments, quote: str) -> str:
    emoji_count = convert_number_to_emoji(unique_segments_count)
    response = (
        f"🔍 *Wyniki wyszukiwania* 🔍\n"
        f"👁️ *Znaleziono:* {emoji_count} pasujących cytatów 👁️\n\n"
    )
    segment_lines = []

    for i, segment in enumerate(segments[:5], start=1):
        segment_info = format_segment(segment)
        line = (
            f"{convert_number_to_emoji(i)}  | 📺 {segment_info.episode_formatted} | 🕒 {segment_info.time_formatted}\n"
            f"   👉  {segment_info.episode_title}"
        )
        segment_lines.append(line)

    response += f"```Cytat: \"{quote}\" \n".replace(" ", "\u00A0") + "\n\n".join(segment_lines) + "\n```"
    return response


def get_log_search_results_sent_message(quote: str, username: str) -> str:
    return f"Search results for quote '{quote}' sent to user '{username}'."
