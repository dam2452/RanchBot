from typing import (
    Dict,
    List,
    Union,
)


def format_episode_list_response(season: int, episodes: List[Dict[str, Union[str, int]]], season_info: Dict[str, int]) -> str:
    response = f"📃 Lista odcinków dla sezonu {season}:\n\n```\n"

    episodes_in_previous_seasons = sum(
        season_info[str(s)] for s in range(1, season)
    )

    for episode in episodes:
        absolute_episode_number = episode["episode_number"]
        season_episode_number = absolute_episode_number - episodes_in_previous_seasons

        viewership = episode.get("viewership")
        formatted_viewership = (
            f"{viewership:,}".replace(",", ".") if viewership is not None else "N/A"
        )

        response += f"🎬 {episode['title']}: S{season:02d}E{season_episode_number:02d} ({absolute_episode_number}) \n"
        response += f"📅 Data premiery: {episode['premiere_date']}\n"
        response += f"👀 Oglądalność: {formatted_viewership}\n\n"

    response += "```"
    return response

def get_no_episodes_found_message(season: int) -> str:
    return f"❌ Nie znaleziono odcinków dla sezonu {season}."


def get_log_no_episodes_found_message(season: int) -> str:
    return f"No episodes found for season {season}."


def get_log_episode_list_sent_message(season: int, username: str) -> str:
    return f"Sent episode list for season {season} to user '{username}'."


def get_invalid_args_count_message() -> str:
    return "📋 Podaj poprawną komendę w formacie: /odcinki <sezon>. Przykład: /odcinki 2"


def get_season_11_petition_message() -> str:
    return (
        "📢 Sezon 11 nie jest jeszcze dostępny. "
        "Podpisz petycję, aby pomóc go zrealizować! "
        "[Link do petycji](https://www.petycjeonline.com/zgoda_na_realizacj_scenariusza_i_wydanie_ksiki_ranczo_zemsta_wiedm#form)"
    )
