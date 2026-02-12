from pathlib import Path
from typing import Optional

from preprocessor.config.step_configs import CharacterReferenceConfig
from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.scraping.reference_processor import CharacterReferenceProcessor


class CharacterReferenceStep(
    PipelineStep[SourceVideo, SourceVideo, CharacterReferenceConfig],
):
    def execute(
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> Optional[SourceVideo]:
        characters_path, output_dir = self._get_paths()
        self._validate_characters_file(characters_path)

        if output_dir.exists() and any(output_dir.iterdir()) and not context.force_rerun:
            context.logger.info(f"Character references already exist in: {output_dir}")
            return input_data

        self._process_character_references(characters_path, output_dir, context)

        return input_data

    @property
    def name(self) -> str:
        return "process_character_references"

    @property
    def is_global(self) -> bool:
        return True

    def _get_paths(self) -> tuple[Path, Path]:
        characters_path = Path(self.config.characters_file)
        output_dir = Path(self.config.output_dir)
        return characters_path, output_dir

    @staticmethod
    def _validate_characters_file(characters_path: Path) -> None:
        if not characters_path.exists():
            raise FileNotFoundError(
                f"Characters file not found: {characters_path}. "
                f"Run scrape_characters first.",
            )


    def _process_character_references(
        self,
        characters_path: Path,
        output_dir: Path,
        context: ExecutionContext,
    ) -> None:
        context.logger.info(f"Processing character references from {characters_path}")

        processor = CharacterReferenceProcessor(
            {
                "characters_file": characters_path,
                "output_dir": output_dir,
                "search_engine": self.config.search_engine,
                "images_per_character": self.config.images_per_character,
            },
        )

        exit_code = processor.work()

        if exit_code != 0:
            raise RuntimeError(
                f"Character reference processor failed with exit code {exit_code}",
            )

        context.logger.info(f"Character references saved to: {output_dir}")
