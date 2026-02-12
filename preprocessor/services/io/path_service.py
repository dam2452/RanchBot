from pathlib import Path
from typing import TYPE_CHECKING

from preprocessor.config.output_paths import get_base_output_dir
from preprocessor.services.core.environment import Environment

if TYPE_CHECKING:
    from preprocessor.services.episodes.episode_manager import EpisodeInfo


class PathService:

    def __init__(self, series_name: str) -> None:
        self._series_name: str = series_name.lower()

    def build_filename(
        self, episode_info: 'EpisodeInfo', extension: str = 'json', suffix: str = '',
    ) -> str:
        base: str = f'{self._series_name}_{episode_info.episode_code()}'
        suffix_str: str = f'_{suffix}' if suffix else ''
        return f'{base}{suffix_str}.{extension}'

    def get_episode_dir(self, episode_info: 'EpisodeInfo', subdir: str) -> Path:
        base_output_dir: Path = get_base_output_dir(self._series_name)
        return base_output_dir / subdir / episode_info.season_code() / episode_info.episode_num()

    @staticmethod
    def get_input_base() -> Path:
        return Path('/input_data') if Environment.is_docker() else Path('preprocessor/input_data')

    @staticmethod
    def get_output_base() -> Path:
        return Path('/app/output_data') if Environment.is_docker() else Path('preprocessor/output_data')
