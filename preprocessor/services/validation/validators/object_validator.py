from typing import TYPE_CHECKING

from preprocessor.config.settings_instance import settings
from preprocessor.services.validation.validators.base_validator import BaseValidator
from preprocessor.services.validation.validators.validation_helpers import (
    JsonDirectoryValidationHelper,
    VisualizationValidationHelper,
)

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class ObjectValidator(BaseValidator):
    def validate(self, stats: 'EpisodeStats') -> None:
        self.__validate_object_detections(stats)
        self.__validate_object_visualizations(stats)

    @staticmethod
    def __validate_object_detections(stats: 'EpisodeStats') -> None:
        JsonDirectoryValidationHelper.validate_json_directory(
            stats,
            settings.output_subdirs.object_detections,
            'object_detections_count',
            'object_detections',
            exclude_pattern='visualizations',
        )

    @staticmethod
    def __validate_object_visualizations(stats: 'EpisodeStats') -> None:
        VisualizationValidationHelper.validate_visualizations(
            stats,
            settings.output_subdirs.object_visualizations,
            'object_visualizations_count',
            'visualization',
        )
