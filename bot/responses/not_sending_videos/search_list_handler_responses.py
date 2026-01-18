from typing import (
    Dict,
    List,
    Union,
)

from bot.utils.functions import format_segment


def get_no_previous_search_results_message() -> str:
    return "🔍 Nie znaleziono wcześniejszych wyników wyszukiwania.🔍"


def get_log_no_previous_search_results_message(chat_id: int) -> str:
    return f"No previous search results found for chat ID {chat_id}."


def format_search_list_response(search_term: str, segments: List[Dict[str, Union[str, int]]],season_info: Dict[str, int]) -> str:
    response = f"🔍 Wyniki dla wyszukiwania: '{search_term}' 🔍\n\n"
    response += f"{'Nr':<4} {'Odcinek':<9} {'Czas':<9} {'Tytuł':<9}\n"
    response += "-" * 50 + "\n"

    for i, segment in enumerate(segments, start=1):
        segment_info = format_segment(segment, season_info)
        response += f"{i:<4} {segment_info.episode_formatted:<9} {segment_info.time_formatted:<9} {segment_info.episode_title:<9}\n"

    return response


def get_log_search_results_sent_message(search_term: str, username: str) -> str:
    return f"List of search results for term '{search_term}' sent to user {username}."
