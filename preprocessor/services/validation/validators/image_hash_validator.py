from __future__ import annotations

from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.episode_stats import EpisodeStats
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator


class ImageHashValidator(BaseValidator):
    def validate(self, stats: EpisodeStats) -> None:
        hash_file = PathService(stats.series_name).get_episode_file_path(
            stats.episode_info, settings.output_subdirs.image_hashes,
        )

        if not hash_file.exists():
            self._add_warning(stats, f'Missing image hashes file: {hash_file.name}')
            return

        result = FileValidator.validate_json_file(hash_file)
        if not result.is_valid:
            self._add_error(stats, f'Invalid image hashes JSON: {result.error_message}')
