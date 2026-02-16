from pathlib import Path
from typing import List

from preprocessor.config.step_configs import ArchiveConfig
from preprocessor.core.artifacts import (
    ArchiveArtifact,
    ProcessedEpisode,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import FileOutput


class ArchiveGenerationStep(
    PipelineStep[ProcessedEpisode, ArchiveArtifact, ArchiveConfig],
):
    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[ProcessedEpisode], context: ExecutionContext,
    ) -> List[ArchiveArtifact]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: ProcessedEpisode, context: ExecutionContext,
    ) -> ArchiveArtifact:
        output_path = self._get_cache_path(input_data, context)
        # Archive generation logic would go here
        return self.__construct_archive_artifact(input_data, output_path)

    def _get_output_descriptors(self) -> List[FileOutput]:
        return [
            FileOutput(
                pattern="{season}/{episode}.zip",
                subdir="archives",
                min_size_bytes=1024 * 100,
            ),
        ]

    def _get_cache_path(
        self, input_data: ProcessedEpisode, context: ExecutionContext,
    ) -> Path:
        return self._get_standard_cache_path(input_data, context)

    def _load_from_cache(
        self,
        cache_path: Path,
        input_data: ProcessedEpisode,
        context: ExecutionContext,
    ) -> ArchiveArtifact:
        return self.__construct_archive_artifact(input_data, cache_path)

    @staticmethod
    def __construct_archive_artifact(
        input_data: ProcessedEpisode, output_path: Path,
    ) -> ArchiveArtifact:
        return ArchiveArtifact(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
        )
