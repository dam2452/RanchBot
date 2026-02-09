from pathlib import Path

from preprocessor.config.config import get_base_output_dir


class PathManager:
    def __init__(self, series_name: str):
        self._series_name = series_name.lower()
        self._base_output_dir = get_base_output_dir(self._series_name)

    @property
    def series_name(self) -> str:
        return self._series_name

    @property
    def base_output_dir(self) -> Path:
        return self._base_output_dir

    def build_path(
        self,
        episode_info,
        subdir: str,
        filename: str,
    ) -> Path:
        season_code = episode_info.season_code()
        episode_code = episode_info.episode_num()

        path = self._base_output_dir / subdir / season_code / episode_code / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        return path

    def build_season_path(
        self,
        episode_info,
        subdir: str,
        filename: str,
    ) -> Path:
        season_code = episode_info.season_code()

        path = self._base_output_dir / subdir / season_code / filename
        path.parent.mkdir(parents=True, exist_ok=True)

        return path

    def get_episode_dir(self, episode_info, subdir: str) -> Path:
        season_code = episode_info.season_code()
        episode_code = episode_info.episode_num()
        episode_dir = self._base_output_dir / subdir / season_code / episode_code
        episode_dir.mkdir(parents=True, exist_ok=True)
        return episode_dir
