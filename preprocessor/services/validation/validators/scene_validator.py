import json
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
)

from preprocessor.config.config import settings
from preprocessor.config.constants import OUTPUT_FILE_PATTERNS
from preprocessor.services.io.path_manager import PathManager
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class SceneValidator(BaseValidator):

    def validate(self, stats: 'EpisodeStats') -> None:
        scenes_dir = PathManager(stats.series_name).get_episode_dir(
            stats.episode_info, settings.output_subdirs.scenes,
        )
        scenes_file = scenes_dir / f"{stats.series_name}_{stats.episode_info.episode_code()}{OUTPUT_FILE_PATTERNS['scenes_suffix']}"

        if not scenes_file.exists():
            self._add_error(stats, f'Missing scenes file: {scenes_file}')
            return

        result = FileValidator.validate_json_file(scenes_file)
        if not result.is_valid:
            self._add_error(stats, f'Invalid scenes JSON: {result.error_message}')
            return

        data = self.__load_json_safely(scenes_file)
        if not data:
            self._add_error(stats, f'Error reading scenes: {scenes_file}')
            return

        stats.scenes_count = data.get('total_scenes', 0)
        scenes = data.get('scenes', [])
        if scenes:
            durations = [scene.get('duration', 0) for scene in scenes]
            stats.scenes_avg_duration = round(sum(durations) / len(durations), 2)

    @staticmethod
    def __load_json_safely(file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
