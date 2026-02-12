from typing import TYPE_CHECKING

from preprocessor.config.config import (
    get_base_output_dir,
    settings,
)
from preprocessor.config.constants import DEFAULT_VIDEO_EXTENSION
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class VideoValidator(BaseValidator):

    def validate(self, stats: 'EpisodeStats') -> None:
        filename = f'{stats.series_name.lower()}_{stats.episode_info.episode_code()}{DEFAULT_VIDEO_EXTENSION}'
        season_dir = get_base_output_dir(stats.series_name) / settings.output_subdirs.video / stats.episode_info.season_code()
        video_file = season_dir / filename

        if not video_file.exists():
            self._add_warning(stats, f'Missing video file: {video_file}')
            return

        result = FileValidator.validate_video_file(video_file)
        if not result.is_valid:
            self._add_error(stats, f'Invalid video: {result.error_message}')
            return

        stats.video_size_mb = result.metadata['size_mb']
        stats.video_duration = result.metadata['duration']
        stats.video_codec = result.metadata['codec']
        stats.video_resolution = (result.metadata['width'], result.metadata['height'])
