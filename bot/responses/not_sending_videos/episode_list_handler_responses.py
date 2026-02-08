from typing import List

from bot.types import (
    EpisodeInfo,
    SeasonInfoDict,
)
from bot.utils.functions import convert_number_to_emoji


def format_episode_list_response(season: int, episodes: List[EpisodeInfo], season_info: SeasonInfoDict) -> str:
    if season == 0:
        response = "```🎬 Specjalne 🎬 \n".replace(" ", "\u00A0")
    else:
        season_emoji = convert_number_to_emoji(season)
        response = f"```Sezon {season_emoji} \n".replace(" ", "\u00A0")

    episodes_in_previous_seasons_from_1 = sum(
        season_info[str(s)] for s in range(1, season) if str(s) in season_info
    )

    for idx, episode in enumerate(episodes, start=1):
        if season == 0:
            episode_display = f"Spec-{idx}"
            episode_with_number = episode_display
        else:
            absolute_episode_number = episodes_in_previous_seasons_from_1 + idx
            season_episode_number = idx
            episode_display = f"S{season:02d}E{season_episode_number:02d}"
            episode_with_number = f"{episode_display} ({absolute_episode_number})"

        viewership = episode.get("viewership")
        if viewership != "Unknown":
            try:
                viewership_num = float(str(viewership).replace(",", "").replace(".", ""))
                formatted_viewership = f"{viewership_num:,.0f}".replace(",", ".")
            except (ValueError, AttributeError):
                formatted_viewership = str(viewership)
        else:
            formatted_viewership = "N/A"

        response += f"🎬 {episode['title']}: {episode_with_number} \n"
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


def format_season_list_response(season_info: SeasonInfoDict) -> str:
    def _format_episode_count(count: int) -> str:
        if count == 1:
            return "1 odcinek"
        if 2 <= count <= 4 or (count > 20 and count % 10 in {2, 3, 4}):
            return f"{count} odcinki"
        return f"{count} odcinków"

    sorted_seasons = sorted(season_info.items(), key=lambda x: int(x[0]))
    season_lines = []

    for season_str, episode_count in sorted_seasons:
        if season_str == "0":
            line = f"🎬 Specjalne 🎬 - {_format_episode_count(episode_count)}"
        else:
            season_num = int(season_str)
            emoji = convert_number_to_emoji(season_num)
            line = f"Sezon {emoji} - {_format_episode_count(episode_count)}"
        season_lines.append(line)

    response = "```📺 LISTA SEZONÓW \n".replace(" ", "\u00A0") + "\n\n".join(season_lines) + "\n```\n\n💡 Użyj /odcinki <sezon> aby zobaczyć szczegóły"
    return response


def get_invalid_args_count_message() -> str:
    return "📋 Podaj poprawną komendę w formacie: /odcinki [sezon]. Przykład: /odcinki 2 lub /odcinki (lista sezonów)"
