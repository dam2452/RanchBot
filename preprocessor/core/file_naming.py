from pathlib import Path
from typing import Optional

from preprocessor.core.constants import (
    FILE_EXTENSIONS,
    FILE_SUFFIXES,
)


class FileNamingConventions:
    def __init__(self, series_name: str):
        self.series_name = series_name.lower()

    def build_base_filename(self, episode_info) -> str:
        return f"{self.series_name}_{episode_info.episode_code()}"

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
