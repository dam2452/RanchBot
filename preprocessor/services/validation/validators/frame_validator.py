from typing import TYPE_CHECKING

from preprocessor.config.constants import OUTPUT_FILE_PATTERNS
from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class FrameValidator(BaseValidator):

    def validate(self, stats: 'EpisodeStats') -> None:
        frames_dir = PathService(stats.series_name).get_episode_dir(
            stats.episode_info, settings.output_subdirs.frames,
        )

        if not frames_dir.exists():
            self._add_warning(
                stats, f'Missing {settings.output_subdirs.frames} directory: {frames_dir}',
            )
            return

        frame_files = sorted(frames_dir.glob(OUTPUT_FILE_PATTERNS['frame']))
        if not frame_files:
            self._add_warning(stats, f'No frames found in {settings.output_subdirs.frames}/')
            return

        stats.exported_frames_count = len(frame_files)
        total_size = 0
        resolutions = []
        invalid_count = 0

        for frame_file in frame_files:
            result = FileValidator.validate_image_file(frame_file)
            if result.is_valid:
                total_size += result.metadata['size_mb']
                resolutions.append((result.metadata['width'], result.metadata['height']))
            else:
                invalid_count += 1
                self._add_error(stats, f'Invalid frame {frame_file.name}: {result.error_message}')

        if invalid_count > 0:
            self._add_warning(stats, f'{invalid_count} invalid frames found')

        stats.exported_frames_total_size_mb = round(total_size, 2)
        if resolutions:
            most_common_res = max(set(resolutions), key=resolutions.count)
            stats.exported_frames_avg_resolution = most_common_res
