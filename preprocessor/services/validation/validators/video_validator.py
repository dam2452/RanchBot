from pathlib import Path
from typing import TYPE_CHECKING

from preprocessor.config.constants import DEFAULT_VIDEO_EXTENSION
from preprocessor.config.output_paths import get_base_output_dir
from preprocessor.config.settings_instance import settings
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class VideoValidator(BaseValidator):
    def validate(self, stats: 'EpisodeStats') -> None:
        video_path = self.__resolve_video_file_path(stats)

        if not video_path.exists():
            self._add_warning(stats, f'Missing video file: {video_path}')
            return

        result = FileValidator.validate_video_file(video_path)
        if not result.is_valid:
            self._add_error(stats, f'Invalid video: {result.error_message}')
            return

        self.__populate_video_metrics(stats, result.metadata)

    @staticmethod
    def __resolve_video_file_path(stats: 'EpisodeStats') -> Path:
        filename = f'{stats.series_name.lower()}_{stats.episode_info.episode_code()}{DEFAULT_VIDEO_EXTENSION}'
        season_dir = (
            get_base_output_dir(stats.series_name) /
            settings.output_subdirs.video /
            stats.episode_info.season_code()
        )
        return season_dir / filename

    @staticmethod
    def __populate_video_metrics(stats: 'EpisodeStats', metadata: dict) -> None:
        stats.video_size_mb = metadata['size_mb']
        stats.video_duration = metadata['duration']
        stats.video_codec = metadata['codec']
        stats.video_resolution = (metadata['width'], metadata['height'])
