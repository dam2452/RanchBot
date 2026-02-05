from typing import (
    Dict,
    List,
    Union,
)


def format_episode_list_response(season: int, episodes: List[Dict[str, Union[str, int]]], season_info: Dict[str, int]) -> str:
    if season == 0:
        response = "📃 Lista odcinków Specjalnych:\n\n```\n"
    else:
        response = f"📃 Lista odcinków dla sezonu {season}:\n\n```\n"

    episodes_in_previous_seasons_from_1 = sum(
        season_info[str(s)] for s in range(1, season) if str(s) in season_info
    )

    for idx, episode in enumerate(episodes, start=1):
        if season == 0:
            episode_display = f"Spec-{idx}"
            absolute_episode_number = f"Spec-{idx}"
        else:
            absolute_episode_number = episodes_in_previous_seasons_from_1 + idx
            season_episode_number = idx
            episode_display = f"S{season:02d}E{season_episode_number:02d}"

        viewership = episode.get("viewership")
        if viewership is not None and viewership != "Unknown":
            try:
                viewership_num = float(str(viewership).replace(",", "").replace(".", ""))
                formatted_viewership = f"{viewership_num:,.0f}".replace(",", ".")
            except (ValueError, AttributeError):
                formatted_viewership = str(viewership)
        else:
            formatted_viewership = "N/A"

        response += f"🎬 {episode['title']}: {episode_display} ({absolute_episode_number}) \n"
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


def format_season_list_response(season_info: Dict[str, int]) -> str:
    response = "📃 Lista sezonów:\n\n```\n"

    sorted_seasons = sorted(season_info.items(), key=lambda x: int(x[0]))

    for season_str, episode_count in sorted_seasons:
        if season_str == "0":
            response += f"📺 Specjalne: {episode_count} odcinków\n"
        else:
            response += f"📺 Sezon {season_str}: {episode_count} odcinków\n"

    response += "```\n\n💡 Użyj /odcinki <sezon> aby zobaczyć szczegóły odcinków z danego sezonu."
    return response


def get_invalid_args_count_message() -> str:
    return "📋 Podaj poprawną komendę w formacie: /odcinki [sezon]. Przykład: /odcinki 2 lub /odcinki (lista sezonów)"
