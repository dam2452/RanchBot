from pathlib import Path
from typing import TYPE_CHECKING

from preprocessor.lib.io.path_service import PathService

if TYPE_CHECKING:
    from preprocessor.lib.episodes.episode_manager import EpisodeInfo


class PathManager:
    def __init__(self, series_name: str) -> None:
        self._service: PathService = PathService(series_name)

    def build_filename(
        self, episode_info: 'EpisodeInfo', extension: str = 'json', suffix: str = '',
    ) -> str:
        return self._service.build_filename(episode_info, extension, suffix)

    def get_episode_dir(self, episode_info: 'EpisodeInfo', subdir: str) -> Path:
        return self._service.get_episode_dir(episode_info, subdir)
