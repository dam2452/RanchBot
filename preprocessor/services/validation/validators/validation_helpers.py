from pathlib import Path
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
    Tuple,
)

from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.file_validators import FileValidator

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class JsonDirectoryValidationHelper:
    @staticmethod
    def validate_json_directory(
            stats: 'EpisodeStats',
            subdir: str,
            count_attr: Optional[str],
            context_name: str,
            exclude_pattern: Optional[str] = None,
            check_anomalies: bool = True,
    ) -> None:
        dir_path = PathService(stats.series_name).get_episode_dir(stats.episode_info, subdir)

        if not dir_path.exists():
            stats.warnings.append(f'Missing {subdir} directory')
            return

        count, sizes, errors = JsonDirectoryValidationHelper.__analyze_json_files(dir_path, exclude_pattern)

        if count == 0:
            stats.warnings.append(f'No JSON files in {subdir}/')
            return

        if count_attr:
            setattr(stats, count_attr, count)

        stats.errors.extend(errors)

        if check_anomalies:
            JsonDirectoryValidationHelper.__perform_size_anomaly_check(stats, sizes, context_name)

    @staticmethod
    def __analyze_json_files(
            directory: Path,
            exclude_pattern: Optional[str],
    ) -> Tuple[int, List[int], List[str]]:
        json_files = [
            f for f in directory.glob('*.json')
            if not exclude_pattern or exclude_pattern not in str(f)
        ]

        if not json_files:
            return 0, [], []

        sizes: List[int] = []
        errors: List[str] = []

        for json_file in json_files:
            result = FileValidator.validate_json_file(json_file)
            if not result.is_valid:
                errors.append(f'Invalid JSON {json_file.name}: {result.error_message}')
            else:
                sizes.append(json_file.stat().st_size)

        return len(json_files), sizes, errors

    @staticmethod
    def __perform_size_anomaly_check(
            stats: 'EpisodeStats',
            sizes: List[int],
            folder_name: str,
            threshold: float = 0.2,
    ) -> None:
        if len(sizes) < 2:
            return

        avg_size = sum(sizes) / len(sizes)
        if avg_size == 0:
            return

        for i, size in enumerate(sizes):
            deviation = abs(size - avg_size) / avg_size
            if deviation > threshold:
                stats.warnings.append(
                    f'{folder_name} file #{i + 1} size deviation: {deviation * 100:.1f}% from average',
                )


class VisualizationValidationHelper:
    @staticmethod
    def validate_visualizations(
            stats: 'EpisodeStats',
            subdir: str,
            count_attr: str,
            context_name: str,
    ) -> None:
        viz_dir = PathService(stats.series_name).get_episode_dir(stats.episode_info, subdir)
        total, invalid, errors = VisualizationValidationHelper.__scan_images(viz_dir)

        if total == 0 and viz_dir.exists():
            stats.warnings.append(f'No visualization images in {subdir}/')
            return

        if total > 0:
            setattr(stats, count_attr, total)
            stats.errors.extend(errors)
            if invalid > 0:
                stats.warnings.append(f'{invalid} invalid {context_name} images found')

    @staticmethod
    def __scan_images(
            directory: Path,
            extensions: Tuple[str, ...] = ('*.jpg', '*.png'),
    ) -> Tuple[int, int, List[str]]:
        if not directory.exists():
            return 0, 0, []

        image_files: List[Path] = []
        for ext in extensions:
            image_files.extend(directory.glob(ext))

        if not image_files:
            return 0, 0, []

        invalid_count = 0
        errors: List[str] = []

        for img_file in image_files:
            result = FileValidator.validate_image_file(img_file)
            if not result.is_valid:
                invalid_count += 1
                errors.append(f'Invalid image {img_file.name}: {result.error_message}')

        return len(image_files), invalid_count, errors
