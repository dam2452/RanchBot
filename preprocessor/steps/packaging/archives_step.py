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


class ArchiveGenerationStep(PipelineStep[ProcessedEpisode, ArchiveArtifact, ArchiveConfig]):
    def get_output_descriptors(self) -> List[FileOutput]:
        return [
            FileOutput(
                pattern="{season}/{episode}.zip",
                subdir="archives",
                min_size_bytes=1024*100,
            ),
        ]

    @property
    def name(self) -> str:
        return 'archive_generation'

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[ProcessedEpisode], context: ExecutionContext,
    ) -> List[ArchiveArtifact]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def execute(
            self, input_data: ProcessedEpisode, context: ExecutionContext,
    ) -> ArchiveArtifact:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached archive'):
            return self.__construct_archive_artifact(input_data, output_path)

        context.logger.info(f'Generating archive for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_archive_artifact(input_data, output_path)

    def __resolve_output_path(
            self, input_data: ProcessedEpisode, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            {
                'season': input_data.episode_info.season_code(),
                'episode': input_data.episode_info.episode_code(),
            },
        )

    @staticmethod
    def __construct_archive_artifact(
            input_data: ProcessedEpisode, output_path: Path,
    ) -> ArchiveArtifact:
        return ArchiveArtifact(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
        )
