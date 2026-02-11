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
        output_filename: str = f'{context.series_name}_{input_data.episode_info.episode_code()}_archive.zip'
        output_path: Path = context.get_output_path(input_data.episode_info, 'archives', output_filename)
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached archive)')
                return ArchiveArtifact(episode_id=input_data.episode_id, episode_info=input_data.episode_info, path=output_path)
        context.logger.info(f'Generating archive for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)
        context.mark_step_completed(self.name, input_data.episode_id)
        return ArchiveArtifact(episode_id=input_data.episode_id, episode_info=input_data.episode_info, path=output_path)

    @property
    def name(self) -> str:
        return 'archive_generation'
