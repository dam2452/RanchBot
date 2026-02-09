from pathlib import Path
from typing import Optional

from preprocessor.config.config import get_base_output_dir
from preprocessor.core.constants import (
    FILE_EXTENSIONS,
    FILE_SUFFIXES,
)


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

    def build_base_filename(self, episode_info) -> str:
        return f"{self._series_name}_{episode_info.episode_code()}"

    def build_filename(
        self,
        episode_info,
        extension: str = "json",
        suffix: Optional[str] = None,
    ) -> str:
        base = self.build_base_filename(episode_info)
        suffix_str = FILE_SUFFIXES.get(suffix, suffix) if suffix else ""
        ext = FILE_EXTENSIONS.get(extension, f".{extension}")
        return f"{base}{suffix_str}{ext}"

    @staticmethod
    def parse_base_filename(filename: str) -> str:
        name = Path(filename).stem
        for suffix_value in FILE_SUFFIXES.values():
            if name.endswith(suffix_value):
                return name[:-len(suffix_value)]
        return name

    @staticmethod
    def add_suffix_to_filename(filename: str, suffix: str) -> str:
        path = Path(filename)
        suffix_str = FILE_SUFFIXES.get(suffix, suffix) if suffix else ""
        return str(path.parent / f"{path.stem}{suffix_str}{path.suffix}")

    @staticmethod
    def get_suffix(suffix_key: str) -> str:
        return FILE_SUFFIXES.get(suffix_key, "")
