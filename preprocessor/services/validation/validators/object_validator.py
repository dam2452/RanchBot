from __future__ import annotations

from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.episode_stats import EpisodeStats
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator
from preprocessor.services.validation.validators.validation_helpers import VisualizationValidationHelper


class ObjectValidator(BaseValidator):
    def validate(self, stats: EpisodeStats) -> None:
        self.__validate_object_detections(stats)
        self.__validate_object_visualizations(stats)

    @staticmethod
    def __validate_object_detections(stats: EpisodeStats) -> None:
        detections_file = PathService(stats.series_name).get_episode_file_path(
            stats.episode_info, settings.output_subdirs.object_detections,
        )

        if not detections_file.exists():
            stats.warnings.append(f'Missing object detections file: {detections_file.name}')
            return

        result = FileValidator.validate_json_file(detections_file)
        if not result.is_valid:
            stats.errors.append(f'Invalid object detections JSON: {result.error_message}')

    @staticmethod
    def __validate_object_visualizations(stats: EpisodeStats) -> None:
        VisualizationValidationHelper.validate_visualizations(
            stats,
            settings.output_subdirs.object_visualizations,
            'object_visualizations_count',
            'visualization',
        )
