from typing import List

from bot.responses.bot_response import BotResponse
from bot.types import SearchSegment
from bot.utils.functions import format_segment


def get_no_previous_search_results_message() -> str:
    return BotResponse.warning("BRAK POPRZEDNICH WYNIKÓW", "Nie znaleziono wczesniejszych wynikow wyszukiwania")


def get_log_no_previous_search_results_message(chat_id: int) -> str:
    return f"No previous search results found for chat ID {chat_id}."


def format_search_list_response(search_term: str, segments: List[SearchSegment]) -> str:
    lines = [f"{'Nr':<4} {'Odcinek':<9} {'Czas':<9} {'Tytul':<9}", "=" * 50]

    for i, segment in enumerate(segments, start=1):
        segment_info = format_segment(segment)
        lines.append(f"{i:<4} {segment_info.episode_formatted:<9} {segment_info.time_formatted:<9} {segment_info.episode_title:<9}")

    return BotResponse.info(f"WYNIKI: {search_term}", "\n".join(lines))


def get_log_search_results_sent_message(search_term: str, username: str) -> str:
    return f"List of search results for term '{search_term}' sent to user {username}."
