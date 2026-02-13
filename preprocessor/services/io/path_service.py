from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Optional,
)

from preprocessor.config.output_paths import get_base_output_dir
from preprocessor.services.core.environment import Environment

if TYPE_CHECKING:
    from preprocessor.services.episodes.episode_manager import EpisodeInfo


class PathService:
    def __init__(self, series_name: str) -> None:
        self.__series_name = series_name.lower()

    def build_filename(
        self,
        episode_info: 'EpisodeInfo',
        extension: str = 'json',
        suffix: Optional[str] = None,
    ) -> str:
        base = f'{self.__series_name}_{episode_info.episode_code()}'
        suffix_str = f'_{suffix}' if suffix else ''
        return f'{base}{suffix_str}.{extension}'

    def get_episode_dir(self, episode_info: 'EpisodeInfo', subdir: str) -> Path:
        base_output_dir = get_base_output_dir(self.__series_name)
        return base_output_dir / subdir / episode_info.season_code() / episode_info.episode_num()

    @staticmethod
    def get_input_base() -> Path:
        if Environment.is_docker():
            return Path('/input_data')
        return Path('preprocessor/input_data')

    @staticmethod
    def get_output_base() -> Path:
        if Environment.is_docker():
            return Path('/app/output_data')
        return Path('preprocessor/output_data')
