# pylint: disable=duplicate-code
from pathlib import Path
from typing import (
    List,
    Tuple,
)

from preprocessor.config.output_paths import get_base_output_dir
from preprocessor.config.step_configs import CharacterReferenceProcessorConfig
from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    DirectoryOutput,
    OutputDescriptor,
)
from preprocessor.services.scraping.reference_processor import CharacterReferenceProcessor


class CharacterReferenceProcessorStep(
    PipelineStep[SourceVideo, SourceVideo, CharacterReferenceProcessorConfig],
):
    @property
    def is_global(self) -> bool:
        return True

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        return [
            DirectoryOutput(
                pattern="character_references_processed",
                subdir="",
                expected_file_pattern="**/face_vector.npy",
                min_files=1,
                min_size_per_file_bytes=100,
            ),
        ]

    def _get_cache_path(
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> Path:
        _, output_dir = self.__resolve_paths(context)
        return output_dir

    def _load_from_cache(
        self, cache_path: Path, input_data: SourceVideo, context: ExecutionContext,
    ) -> SourceVideo:
        context.logger.info(f"Character reference vectors already exist in: {cache_path}")
        return input_data

    def _process(
        self, input_data: SourceVideo, context: ExecutionContext,
    ) -> SourceVideo:
        characters_dir, output_dir = self.__resolve_paths(context)
        self.__validate_input_directory(characters_dir)
        self.__run_reference_processor(characters_dir, output_dir, context)
        return input_data

    @staticmethod
    def __resolve_paths(context: ExecutionContext) -> Tuple[Path, Path]:
        base_dir = get_base_output_dir(context.series_name)
        return base_dir / 'character_faces', base_dir / 'character_references_processed'

    def __run_reference_processor(
        self,
        characters_dir: Path,
        output_dir: Path,
        context: ExecutionContext,
    ) -> None:
        context.logger.info(f"Processing character reference images from {characters_dir}")

        processor = CharacterReferenceProcessor({
            'characters_dir': characters_dir,
            'output_dir': output_dir,
            'similarity_threshold': self.config.similarity_threshold,
            'interactive': False,
        })

        exit_code = processor.work()
        if exit_code != 0:
            raise RuntimeError(
                f"Character reference processor failed with exit code {exit_code}",
            )

        context.logger.info(f"Character reference vectors saved to: {output_dir}")

    @staticmethod
    def __validate_input_directory(characters_dir: Path) -> None:
        if not characters_dir.exists():
            raise FileNotFoundError(
                f"Character faces directory not found: {characters_dir}. "
                f"Run character_reference step first.",
            )
