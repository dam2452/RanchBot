from __future__ import annotations

from preprocessor.config.settings_instance import settings
from preprocessor.services.validation.episode_stats import EpisodeStats
from preprocessor.services.validation.validators.base_validator import BaseValidator
from preprocessor.services.validation.validators.validation_helpers import VisualizationValidationHelper


class CharacterValidator(BaseValidator):
    def validate(self, stats: EpisodeStats) -> None:
        VisualizationValidationHelper.validate_visualizations(
            stats,
            settings.output_subdirs.character_visualizations,
            'character_visualizations_count',
            'character visualization',
        )
