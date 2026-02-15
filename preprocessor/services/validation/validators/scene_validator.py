from __future__ import annotations

from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.constants import OUTPUT_FILE_PATTERNS
from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.episode_stats import EpisodeStats
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator


class SceneValidator(BaseValidator):
    def validate(self, stats: EpisodeStats) -> None:
        scenes_file = self.__resolve_scenes_file(stats)

        if not self._check_path_exists(scenes_file, stats, f'Missing scenes file: {scenes_file}'):
            return

        if not self.__validate_json_integrity(stats, scenes_file):
            return

        data = self._load_json_safely(scenes_file)
        if data:
            self.__extract_scene_stats(stats, data)

    @staticmethod
    def __resolve_scenes_file(stats: EpisodeStats) -> Path:
        scenes_dir = PathService(stats.series_name).get_episode_dir(
            stats.episode_info, settings.output_subdirs.scenes,
        )
        suffix = OUTPUT_FILE_PATTERNS['scenes_suffix']
        return scenes_dir / f"{stats.series_name}_{stats.episode_info.episode_code()}{suffix}"

    def __validate_json_integrity(self, stats: EpisodeStats, file_path: Path) -> bool:
        result = FileValidator.validate_json_file(file_path)
        if not result.is_valid:
            self._add_error(stats, f'Invalid scenes JSON: {result.error_message}')
            return False
        return True

    @staticmethod
    def __extract_scene_stats(stats: EpisodeStats, data: Dict[str, Any]) -> None:
        stats.scenes_count = data.get('total_scenes', 0)
        scenes: List[Dict[str, Any]] = data.get('scenes', [])

        if scenes:
            durations = [s.get('duration', 0) for s in scenes]
            stats.scenes_avg_duration = round(sum(durations) / len(durations), 2)
