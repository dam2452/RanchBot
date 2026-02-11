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
    def __init__(self, config: CharacterReferenceConfig) -> None:
        super().__init__(config)
        self._executed = False

    def execute(
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> Optional[SourceVideo]:
        if self._executed:
            return input_data

        characters_path, output_dir = self._get_paths()
        self._validate_characters_file(characters_path)

        if self._should_skip_processing(output_dir, context):
            self._executed = True
            return input_data

        self._process_character_references(characters_path, output_dir, context)
        self._executed = True

        return input_data

    @property
    def name(self) -> str:
        return "process_character_references"

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

    @staticmethod
    def _should_skip_processing(output_dir: Path, context: ExecutionContext) -> bool:
        if output_dir.exists() and any(output_dir.iterdir()) and not context.force_rerun:
            context.logger.info(f"Character references already exist in: {output_dir}")
            return True
        return False

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
