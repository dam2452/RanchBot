import json
import logging
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.core.constants import SUPPORTED_VIDEO_EXTENSIONS
from preprocessor.core.file_naming import FileNamingConventions

logger = logging.getLogger(__name__)


class EpisodeFileFinder:
    def __init__(self, series_name: str):
        self.file_naming = FileNamingConventions(series_name)

    @staticmethod
    def find_video_file(episode_info, search_dir: Path) -> Optional[Path]:
        if not search_dir.exists():
            return None

        if search_dir.is_file():
            return search_dir

        episode_code = episode_info.episode_code()
        season_dir_name = episode_info.season_code()
        search_dirs = [search_dir / season_dir_name, search_dir]

        for dir_path in search_dirs:
            if not dir_path.exists():
                continue

            for ext in SUPPORTED_VIDEO_EXTENSIONS:
                for video_file in dir_path.glob(f"*{ext}"):
                    if re.search(episode_code, video_file.name, re.IGNORECASE):
                        return video_file

        return None

    def find_transcription_file(
        self,
        episode_info,
        search_dir: Path,
        prefer_segmented: bool = True,
    ) -> Optional[Path]:
        if not search_dir.exists():
            return None

        season_dir_name = episode_info.season_code()
        season_dir = search_dir / season_dir_name
        if not season_dir.exists():
            return None

        if prefer_segmented:
            segmented = season_dir / self.file_naming.build_filename(
                episode_info,
                extension="json",
                suffix="segmented",
            )
            if segmented.exists():
                return segmented

        regular = season_dir / self.file_naming.build_filename(episode_info, extension="json")
        if regular.exists():
            return regular

        return None

    @staticmethod
    def find_scene_timestamps_file(episode_info, search_dir: Path) -> Optional[Path]:
        if not search_dir.exists():
            return None

        episode_code = episode_info.episode_code()
        pattern = f"**/*{episode_code}*_scenes.json"

        for scene_file in search_dir.glob(pattern):
            return scene_file

        return None

    @staticmethod
    def load_scene_timestamps(
        episode_info,
        search_dir: Optional[Path],
        _logger=None,
    ) -> Optional[List[Dict[str, Any]]]:
        if not search_dir:
            return None

        finder = EpisodeFileFinder("")
        scene_file = finder.find_scene_timestamps_file(episode_info, search_dir)
        if not scene_file:
            return None

        try:
            with open(scene_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            if _logger:
                _logger.error(f"Failed to load scene timestamps: {e}")
            return None
