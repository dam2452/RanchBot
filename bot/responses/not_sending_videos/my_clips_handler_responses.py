from typing import (
    List,
    Union,
)

from bot.database.models import VideoClip
from bot.utils.functions import convert_number_to_emoji


def format_myclips_response(clips: List[VideoClip], username: Union[str, None], full_name: Union[str, None]) -> str:
    clip_lines = []

    user_display_name = f"@{username}" if username else full_name

    for idx, clip in enumerate(clips, start=1):
        if clip.duration:
            minutes, seconds = divmod(clip.duration, 60)
            if minutes:
                length_str = f"{minutes}m{int(seconds)}s"
            else:
                length_str = f"{seconds:.2f}s"
        else:
            length_str = "Brak danych"

        if clip.is_compilation:
            season_episode = "Kompilacja"
        else:
            episode_number_mod = (clip.episode_number - 1) % 13 + 1 if clip.episode_number else "N/A"
            season_episode = f"S{clip.season:02d}E{episode_number_mod:02d}"

        clip_lines.append(
            f"{convert_number_to_emoji(idx)} | 📺 {season_episode} | 🕒 {length_str}\n"
            f"   👉 {clip.name}",
        )

    return (
        f"🎬 *Twoje Zapisane Klipy* 🎬\n"
        f"🎥 *Liczba klipów:* {convert_number_to_emoji(len(clips))} 🎥\n\n"
        f"```Użytkownik: {user_display_name} \n".replace(" ", "\u00A0") + "\n\n".join(clip_lines) + "\n```"
    )


def get_no_saved_clips_message() -> str:
    return "📭 Nie masz zapisanych klipów.📭"


def get_log_no_saved_clips_message(username: str) -> str:
    return f"No saved clips found for user: {username}"


def get_log_saved_clips_sent_message(username: str) -> str:
    return f"List of saved clips sent to user '{username}'."
