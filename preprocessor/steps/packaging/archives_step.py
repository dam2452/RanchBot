from pathlib import Path

from preprocessor.config.step_configs import ArchiveConfig
from preprocessor.core.artifacts import (
    ArchiveArtifact,
    ProcessedEpisode,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext


class ArchiveGenerationStep(PipelineStep[ProcessedEpisode, ArchiveArtifact, ArchiveConfig]):

    def execute(self, input_data: ProcessedEpisode, context: ExecutionContext) -> ArchiveArtifact:
        output_path = self._get_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached archive'):
            return self._create_archive_artifact(input_data, output_path)

        context.logger.info(f'Generating archive for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)
        context.mark_step_completed(self.name, input_data.episode_id)

        return self._create_archive_artifact(input_data, output_path)

    @property
    def name(self) -> str:
        return 'archive_generation'

    @staticmethod
    def _get_output_path(input_data: ProcessedEpisode, context: ExecutionContext) -> Path:
        output_filename: str = f'{context.series_name}_{input_data.episode_info.episode_code()}_archive.zip'
        return context.get_output_path(input_data.episode_info, 'archives', output_filename)


    @staticmethod
    def _create_archive_artifact(input_data: ProcessedEpisode, output_path: Path) -> ArchiveArtifact:
        return ArchiveArtifact(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
        )
