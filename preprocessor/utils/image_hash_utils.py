import json
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.config.config import settings


def load_image_hashes_for_episode(episode_info_dict: Dict[str, Any], logger=None) -> Dict[int, str]:
    season = episode_info_dict.get("season")
    episode = episode_info_dict.get("episode_number")
    if season is None or episode is None:
        return {}

    image_hashes_dir = Path(settings.image_hash.output_dir)
    hashes_episode_dir = image_hashes_dir / f"S{season:02d}" / f"E{episode:02d}"
    hashes_file = hashes_episode_dir / "image_hashes.json"

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
    except Exception as e:  # pylint: disable=broad-exception-caught
        if logger:
            logger.error(f"Failed to load image hashes: {e}")
        return {}
