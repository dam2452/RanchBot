from pathlib import Path
from typing import (
    Optional,
    Tuple,
)

from preprocessor.config.step_configs import CharacterReferenceConfig
from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.characters.reference_downloader import CharacterReferenceDownloader


class CharacterReferenceStep(
    PipelineStep[SourceVideo, SourceVideo, CharacterReferenceConfig],
):
    @property
    def name(self) -> str:
        return "process_character_references"

    @property
    def is_global(self) -> bool:
        return True

    def execute(
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> Optional[SourceVideo]:
        characters_path, output_dir = self.__resolve_paths()
        self.__validate_characters_file(characters_path)

        if self.__should_skip_processing(output_dir, context):
            context.logger.info(f"Character references already exist in: {output_dir}")
            return input_data

        self.__download_character_references(characters_path, output_dir, context)

        return input_data

    def __resolve_paths(self) -> Tuple[Path, Path]:
        characters_path = Path(self.config.characters_file)
        output_dir = Path(self.config.output_dir)
        return characters_path, output_dir

    def __download_character_references(
        self,
        characters_path: Path,
        output_dir: Path,
        context: ExecutionContext,
    ) -> None:
        context.logger.info(f"Downloading character references from {characters_path}")

        downloader = CharacterReferenceDownloader(
            {
                "characters_json": characters_path,
                "output_dir": output_dir,
                "search_engine": self.config.search_engine,
                "images_per_character": self.config.images_per_character,
                "series_name": context.series_name,
            },
        )

        exit_code = downloader.work()

        if exit_code != 0:
            raise RuntimeError(
                f"Character reference downloader failed with exit code {exit_code}",
            )

        context.logger.info(f"Character references saved to: {output_dir}")

    @staticmethod
    def __should_skip_processing(output_dir: Path, context: ExecutionContext) -> bool:
        if context.force_rerun:
            return False
        return output_dir.exists() and any(output_dir.iterdir())

    @staticmethod
    def __validate_characters_file(characters_path: Path) -> None:
        if not characters_path.exists():
            raise FileNotFoundError(
                f"Characters file not found: {characters_path}. "
                f"Run scrape_characters first.",
            )
