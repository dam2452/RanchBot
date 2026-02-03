import logging
from pathlib import Path
import re
from typing import (
    Dict,
    List,
)

from bot.settings import settings


class SeriesScanner:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.data_dir = Path(settings.VIDEO_DATA_DIR)

    def scan_all_series(self) -> List[str]:
        series_set = set()

        if not self.data_dir.exists():
            self.logger.warning(f"Video data directory does not exist: {self.data_dir}")
            return []

        for season_dir in self.data_dir.iterdir():
            if not season_dir.is_dir() or not re.match(r'^S\d{2}$', season_dir.name):
                continue

            for zip_file in season_dir.glob("*.zip"):
                series_name = self._detect_series_from_filename(zip_file.name)
                if series_name:
                    series_set.add(series_name)

        return sorted(list(series_set))

    def scan_series_zips(self, series_name: str) -> List[Path]:
        zip_files = []

        if not self.data_dir.exists():
            return []

        for season_dir in self.data_dir.iterdir():
            if not season_dir.is_dir() or not re.match(r'^S\d{2}$', season_dir.name):
                continue

            for zip_file in season_dir.glob(f"{series_name}_*.zip"):
                zip_files.append(zip_file)

        return sorted(zip_files)

    def scan_series_mp4s(self, series_name: str) -> Dict[str, Path]:
        mp4_map = {}

        if not self.data_dir.exists():
            self.logger.warning(f"Video data directory does not exist: {self.data_dir}")
            return {}

        for season_dir in self.data_dir.iterdir():
            if not season_dir.is_dir() or not re.match(r'^S\d{2}$', season_dir.name):
                continue

            for mp4_file in season_dir.glob(f"{series_name}_*.mp4"):
                episode_code = self._extract_episode_code(mp4_file.name)
                if episode_code:
                    mp4_map[episode_code] = mp4_file

        return mp4_map

    def _detect_series_from_filename(self, filename: str) -> str:
        match = re.match(r'^([a-z0-9_-]+)_S\d{2}E\d{2}', filename, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return None

    def _extract_episode_code(self, filename: str) -> str:
        match = re.search(r'(S\d{2}E\d{2})', filename, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None
