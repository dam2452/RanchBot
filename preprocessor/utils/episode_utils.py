from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    Optional,
)


def get_episode_metadata(
    episodes_info: Optional[Dict[str, Any]],
    season: int,
    episode: int,
) -> Dict[str, Any]:
    if not episodes_info:
        return {
            "season": season,
            "episode_number": episode,
            "title": f"Episode {episode}",
        }

    for season_data in episodes_info.get("seasons", []):
        if season_data.get("season_number") == season:
            for ep_data in season_data.get("episodes", []):
                if ep_data.get("episode_number") == episode:
                    return {
                        "season": season,
                        "episode_number": episode,
                        "title": ep_data.get("title", f"Episode {episode}"),
                        "premiere_date": ep_data.get("premiere_date"),
                        "viewership": ep_data.get("viewership"),
                    }

    return {
        "season": season,
        "episode_number": episode,
        "title": f"Episode {episode}",
    }


def build_output_path(
    output_dir: Path,
    series_name: str,
    season: int,
    episode: int,
    extension: str = ".json",
) -> Path:
    filename = f"{series_name}_S{season:02d}E{episode:02d}{extension}"
    if season == 0:
        season_dir = output_dir / "Specjalne"
    else:
        season_dir = output_dir / f"Sezon {season}"
    return season_dir / filename


def extract_season_episode_from_filename(file_path: Path) -> tuple[int, int]:
    match = re.search(r'S(\d+)E(\d+)', file_path.name, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 1, 1


def extract_episode_number(file_path: Path) -> Optional[int]:
    pattern = r"(?:E(?P<ep>\d+))|(?:_S\d{2}E(?P<ep2>\d+))"
    match = re.search(pattern, file_path.stem, re.IGNORECASE)
    if match:
        episode = match.group("ep") or match.group("ep2")
        return int(episode)
    return None


def find_episode_info_by_absolute(
    episodes_info: Dict[str, Any],
    absolute_episode: int,
) -> Optional[Dict[str, Any]]:
    for season in episodes_info.get("seasons", []):
        season_number = season["season_number"]
        episodes = sorted(season.get("episodes", []), key=lambda ep: ep["episode_number"])
        for idx, ep_data in enumerate(episodes):
            if ep_data.get("episode_number") == absolute_episode:
                return {
                    "season": season_number,
                    "episode_number": idx + 1,
                    "premiere_date": ep_data["premiere_date"],
                    "title": ep_data["title"],
                    "viewership": ep_data["viewership"],
                }
    return None
