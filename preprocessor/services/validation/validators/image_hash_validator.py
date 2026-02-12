from typing import TYPE_CHECKING

from preprocessor.config.settings_instance import settings
from preprocessor.services.validation.validators.base_validator import BaseValidator
from preprocessor.services.validation.validators.validation_helpers import JsonDirectoryValidationHelper

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class ImageHashValidator(BaseValidator):

    def validate(self, stats: 'EpisodeStats') -> None:
        JsonDirectoryValidationHelper.validate_json_directory(
            stats,
            settings.output_subdirs.image_hashes,
            'image_hashes_count',
            'image_hashes',
        )
