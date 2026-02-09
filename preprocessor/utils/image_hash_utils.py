import json
from typing import Dict

from preprocessor.config.config import settings
from preprocessor.core.path_manager import PathManager
from preprocessor.episodes import EpisodeInfo


def load_image_hashes_for_episode(
    episode_info_dict: Dict[str, int],
    series_name: str,
    logger=None,
) -> Dict[int, str]:
    season = episode_info_dict.get("season")
    episode = episode_info_dict.get("episode_number")
    if season is None or episode is None:
        return {}

    path_manager = PathManager(series_name)
    episode_info = EpisodeInfo.create_minimal(season, episode, series_name)

    hashes_episode_dir = path_manager.get_episode_dir(
        episode_info,
        settings.output_subdirs.image_hashes,
    )

    hash_files = list(hashes_episode_dir.glob("*_image_hashes.json"))
    if not hash_files:
        if logger:
            logger.debug(f"Image hashes not found in: {hashes_episode_dir}")
        return {}

    hashes_file = hash_files[0]

    if not hashes_file.exists():
        if logger:
            logger.debug(f"Image hashes not found: {hashes_file}")
        return {}

    try:
        with open(hashes_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        hash_map = {}
        for item in data.get("image_hashes", []):
            frame_num = item.get("frame_number")
            phash = item.get("perceptual_hash")
            if frame_num is not None and phash:
                hash_map[frame_num] = phash

        return hash_map
    except Exception as e:
        if logger:
            logger.error(f"Failed to load image hashes: {e}")
        return {}
