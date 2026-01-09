from dataclasses import dataclass
import json
import logging
from typing import (
    Dict,
    List,
)
import unicodedata

from bot.database.database_manager import UserProfile
from bot.database.models import FormattedSegmentInfo

logger = logging.getLogger(__name__)

@dataclass
class Resolution:
    width: int
    height: int

RESOLUTIONS: Dict[str, Resolution] = {
    "1080p": Resolution(1920, 1080),
    "720p": Resolution(1280, 720),
    "480p": Resolution(854, 480),
}

class InvalidTimeStringException(Exception):
    def __init__(self, time: str) -> None:
        self.message = f"Invalid time string: '{time}'. Upewnij się, że używasz formatu MM:SS\u200B.ms, np. 20:30.11"
        super().__init__(self.message)


def minutes_str_to_seconds(time_str: str) -> float:
    try:
        minutes, seconds = time_str.split(":")
        seconds, milliseconds = seconds.split(".")
        total_seconds = int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000
        return total_seconds
    except (TypeError, ValueError) as e:
        raise InvalidTimeStringException(time_str) from e


def convert_seconds_to_time_str(seconds: int) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def time_str_to_seconds(time_str: str) -> int:
    h, m, s = [int(part) for part in time_str.split(":")]
    return h * 3600 + m * 60 + s


def parse_whitelist_message(
        content: List[str],
) -> UserProfile:
    try:
        user_id = int(content[0])
    except ValueError as exc:
        raise ValueError(f"Invalid user_id: {content[0]} is not a valid integer.") from exc

    return UserProfile(
        user_id=user_id,
        username=content[1] if len(content) > 1 else None,
        full_name=content[2] if len(content) > 2 else None,
        subscription_end=None,
        note=None,
    )


def format_segment(segment: json, season_info: Dict[str, int]) -> FormattedSegmentInfo:
    episode_info = segment.get("episode_info", {})
    total_episode_number = episode_info.get("episode_number", "Unknown")

    if not isinstance(total_episode_number, int):
        return FormattedSegmentInfo(
            episode_formatted="Unknown",
            time_formatted="00:00",
            episode_title=episode_info.get("title", "Unknown"),
        )

    season_number = 1
    episodes_in_previous_seasons = 0
    for season, episode_count in season_info.items():
        if total_episode_number <= (episodes_in_previous_seasons + episode_count):
            break
        episodes_in_previous_seasons += episode_count
        season_number += 1

    episode_number_in_season = total_episode_number - episodes_in_previous_seasons

    season = str(season_number).zfill(2)
    episode_number = str(episode_number_in_season).zfill(2)

    start_time = int(segment["start"])
    minutes, seconds = divmod(start_time, 60)

    return FormattedSegmentInfo(
        episode_formatted=f"S{season}E{episode_number}",
        time_formatted=f"{minutes:02}:{seconds:02}",
        episode_title=episode_info.get("title", "Unknown"),
    )



number_to_emoji: Dict[str, str] = {
    "0": "0️⃣",
    "1": "1️⃣",
    "2": "2️⃣",
    "3": "3️⃣",
    "4": "4️⃣",
    "5": "5️⃣",
    "6": "6️⃣",
    "7": "7️⃣",
    "8": "8️⃣",
    "9": "9️⃣",
}


def convert_number_to_emoji(number: int) -> str:
    return "".join(number_to_emoji.get(digit, digit) for digit in str(number))


def format_user_list(users: List[UserProfile], title: str) -> str:
    user_lines = []

    for idx, user in enumerate(users, start=1):
        line = (
            f"{convert_number_to_emoji(idx)} | 🆔 {user.user_id}\n"
            f"   🧑‍💻 {user.full_name or user.username}\n"
            f"   🗓 Subskrypcja do: {user.subscription_end or 'N/A'}\n"
            f"   📝 Note: {user.note or 'Brak'}"
        )
        user_lines.append(line)

    response = f"📃 {title}:\n"
    response += "```\n" + "\n\n".join(user_lines) + "\n```"
    return response

def remove_diacritics_and_lowercase(text):
    normalized_text = unicodedata.normalize('NFKD', text)
    cleaned_text = ''.join([char for char in normalized_text if not unicodedata.combining(char)])
    return cleaned_text.lower()
