from pathlib import Path
from typing import List

from preprocessor.services.validation.base_result import BaseValidationResult
from preprocessor.services.validation.file_validators import FileValidator


class GlobalValidationResult(BaseValidationResult):
    pass


class GlobalValidator:
    def __init__(self, series_name: str, base_output_dir: Path) -> None:
        self.__series_name = series_name
        self.__base_output_dir = base_output_dir
        self.__result = GlobalValidationResult()

    def validate(self) -> GlobalValidationResult:
        self.__check_main_json_files()
        self.__check_characters_assets()
        self.__check_processing_metadata_store()
        return self.__result

    def __check_main_json_files(self) -> None:
        files = [
            (f'{self.__series_name}_episodes.json', 'episodes_json_valid'),
            (f'{self.__series_name}_characters.json', 'characters_json_valid'),
        ]
        for filename, stats_key in files:
            self.__validate_json_at_path(self.__base_output_dir / filename, stats_key)

    def __check_characters_assets(self) -> None:
        char_dir = self.__base_output_dir / 'characters'
        if not char_dir.exists():
            self.__result.warnings.append('Missing characters/ directory')
            return

        folders = [d for d in char_dir.iterdir() if d.is_dir()]
        self.__result.stats['character_folders_count'] = len(folders)

        if not folders:
            self.__result.warnings.append('No character folders in characters/')
            return

        self.__process_all_character_folders(folders)

    def __process_all_character_folders(self, folders: List[Path]) -> None:
        counters = {'total': 0, 'invalid': 0, 'empty_chars': []}

        for folder in folders:
            images = self.__get_image_files(folder)
            if not images:
                counters['empty_chars'].append(folder.name)
                continue

            counters['total'] += len(images)
            counters['invalid'] += self.__validate_image_batch(images, folder.name)

        self.__result.stats['character_images_count'] = counters['total']
        self.__result.stats['invalid_character_images'] = counters['invalid']

        if counters['empty_chars']:
            self.__result.warnings.append(f'{len(counters["empty_chars"])} characters without images')

    def __validate_image_batch(self, images: List[Path], char_name: str) -> int:
        invalid_count = 0
        for img in images:
            v_res = FileValidator.validate_image_file(img)
            if not v_res.is_valid:
                invalid_count += 1
                self.__result.errors.append(f'Invalid image {char_name}/{img.name}: {v_res.error_message}')
        return invalid_count

    def __check_processing_metadata_store(self) -> None:
        meta_dir = self.__base_output_dir / 'processing_metadata'
        if not meta_dir.exists():
            self.__result.warnings.append('Missing processing_metadata/ directory')
            return

        json_files = list(meta_dir.glob('*.json'))
        self.__result.stats['processing_metadata_files'] = len(json_files)

        for f in json_files:
            v_res = FileValidator.validate_json_file(f)
            if not v_res.is_valid:
                self.__result.errors.append(f'Invalid metadata {f.name}: {v_res.error_message}')

    def __validate_json_at_path(self, path: Path, stats_key: str) -> None:
        if not path.exists():
            self.__result.warnings.append(f'Missing {path.name}')
            return
        v_res = FileValidator.validate_json_file(path)
        if not v_res.is_valid:
            self.__result.errors.append(f'Invalid {path.name}: {v_res.error_message}')
        else:
            self.__result.stats[stats_key] = True

    @staticmethod
    def __get_image_files(folder: Path) -> List[Path]:
        found = []
        for ext in ('*.jpg', '*.jpeg', '*.png', '*.webp'):
            found.extend(folder.glob(ext))
        return found
