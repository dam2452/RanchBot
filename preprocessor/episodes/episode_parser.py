import logging
from pathlib import Path
import re
from typing import Optional

logger = logging.getLogger(__name__)


class EpisodeInfoParser:
    @staticmethod
    def parse_filename(file_path: Path, episode_manager) -> Optional:
        full_path_str = str(file_path)

        match_season_episode = re.search(r'S(\d+)[/\\]?E(\d+)', full_path_str, re.IGNORECASE)
        if match_season_episode:
            season = int(match_season_episode.group(1))
            episode = int(match_season_episode.group(2))
            return episode_manager.get_episode_by_season_and_relative(season, episode)

        logger.error(
            f"Cannot parse episode from filename: {file_path.name}. "
            f"Expected format: S##E## (e.g., S01E05, S10E13). "
            f"Absolute episode numbers (E## without season) are not supported.",
        )
        return None

    @staticmethod
    def get_episode_id(episode_info) -> str:
        return episode_info.episode_code()
