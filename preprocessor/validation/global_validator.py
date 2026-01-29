from pathlib import Path
from typing import List

from preprocessor.config.config import BASE_OUTPUT_DIR
from preprocessor.validation.base_result import BaseValidationResult
from preprocessor.validation.file_validators import (
    validate_image_file,
    validate_json_file,
)


class GlobalValidationResult(BaseValidationResult):
    pass


class GlobalValidator:
    def __init__(
        self,
        series_name: str,
        base_output_dir: Path = BASE_OUTPUT_DIR,
    ):
        self.series_name = series_name
        self.base_output_dir = base_output_dir
        self.result = GlobalValidationResult()

    def validate(self) -> GlobalValidationResult:
        self.__validate_main_json_files()
        self.__validate_characters_folder()
        self.__validate_processing_metadata()
        return self.result

    def __validate_main_json_files(self):
        episodes_file = self.base_output_dir / f"{self.series_name}_episodes.json"
        if episodes_file.exists():
            result = validate_json_file(episodes_file)
            if not result.is_valid:
                self.result.errors.append(f"Invalid {episodes_file.name}: {result.error_message}")
            else:
                self.result.stats["episodes_json_valid"] = True
        else:
            self.result.warnings.append(f"Missing {episodes_file.name}")

        characters_file = self.base_output_dir / f"{self.series_name}_characters.json"
        if characters_file.exists():
            result = validate_json_file(characters_file)
            if not result.is_valid:
                self.result.errors.append(f"Invalid {characters_file.name}: {result.error_message}")
            else:
                self.result.stats["characters_json_valid"] = True
        else:
            self.result.warnings.append(f"Missing {characters_file.name}")

    def __validate_characters_folder(self):
        characters_dir = self.base_output_dir / "characters"
        if not characters_dir.exists():
            self.result.warnings.append("Missing characters/ directory")
            return

        character_folders = [d for d in characters_dir.iterdir() if d.is_dir()]
        if not character_folders:
            self.result.warnings.append("No character folders in characters/")
            return

        self.result.stats["character_folders_count"] = len(character_folders)

        total_images = 0
        invalid_images = 0
        characters_without_images: List[str] = []

        for char_folder in character_folders:
            image_files = (
                list(char_folder.glob("*.jpg")) +
                list(char_folder.glob("*.jpeg")) +
                list(char_folder.glob("*.png")) +
                list(char_folder.glob("*.webp"))
            )

            if not image_files:
                characters_without_images.append(char_folder.name)
                continue

            total_images += len(image_files)

            for img_file in image_files:
                result = validate_image_file(img_file)
                if not result.is_valid:
                    invalid_images += 1
                    self.result.errors.append(
                        f"Invalid character image {char_folder.name}/{img_file.name}: {result.error_message}",
                    )

        self.result.stats["character_images_count"] = total_images
        self.result.stats["invalid_character_images"] = invalid_images

        if characters_without_images:
            self.result.warnings.append(
                f"{len(characters_without_images)} characters without reference images",
            )

    def __validate_processing_metadata(self):
        metadata_dir = self.base_output_dir / "processing_metadata"
        if not metadata_dir.exists():
            self.result.warnings.append("Missing processing_metadata/ directory")
            return

        json_files = list(metadata_dir.glob("*.json"))
        if not json_files:
            self.result.warnings.append("No JSON files in processing_metadata/")
            return

        self.result.stats["processing_metadata_files"] = len(json_files)

        for json_file in json_files:
            result = validate_json_file(json_file)
            if not result.is_valid:
                self.result.errors.append(
                    f"Invalid processing metadata {json_file.name}: {result.error_message}",
                )
