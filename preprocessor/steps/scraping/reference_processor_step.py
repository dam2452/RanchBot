from pathlib import Path
from typing import Tuple

from preprocessor.config.output_paths import get_base_output_dir
from preprocessor.config.step_configs import CharacterReferenceConfig
from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.characters.reference_downloader import CharacterReferenceDownloader


class CharacterReferenceStep(
    PipelineStep[SourceVideo, SourceVideo, CharacterReferenceConfig],
):
    @property
    def is_global(self) -> bool:
        return True

    @property
    def uses_caching(self) -> bool:
        return False

    @property
    def uses_global_completion(self) -> bool:
        return False

    def _process(
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> SourceVideo:
        if self.config.images_per_character == 0:
            context.logger.info("images_per_character=0, skipping character reference download")
            return input_data
        characters_path, output_dir = self.__resolve_paths(context)
        self.__validate_characters_file(characters_path)
        self.__download_character_references(characters_path, output_dir, context)
        return input_data

    @staticmethod
    def __resolve_paths(context: ExecutionContext) -> Tuple[Path, Path]:
        base_dir = get_base_output_dir(context.series_name)
        characters_path = base_dir / f"{context.series_name}_characters.json"
        output_dir = base_dir / "character_faces"
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
                "search_query_template": self.config.search_query_template,
                "force_rerun": context.force_rerun,
            },
        )

        exit_code = downloader.work()

        if exit_code != 0:
            raise RuntimeError(
                f"Character reference downloader failed with exit code {exit_code}",
            )

        context.logger.info(f"Character references saved to: {output_dir}")

    @staticmethod
    def __validate_characters_file(characters_path: Path) -> None:
        if not characters_path.exists():
            raise FileNotFoundError(
                f"Characters file not found: {characters_path}. "
                f"Run scrape_characters first.",
            )
