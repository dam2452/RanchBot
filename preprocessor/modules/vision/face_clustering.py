from pathlib import Path

from preprocessor.config.step_configs import FaceClusteringConfig
from preprocessor.core.artifacts import (
    ClusterData,
    FrameCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext


class FaceClusteringStep(PipelineStep[FrameCollection, ClusterData, FaceClusteringConfig]):

    @property
    def name(self) -> str:
        return 'face_clustering'

    def execute(self, input_data: FrameCollection, context: ExecutionContext) -> ClusterData:
        output_filename: str = f'{context.series_name}_{input_data.episode_info.episode_code()}_clusters.json'
        output_path: Path = context.get_output_path(input_data.episode_info, 'face_clusters', output_filename)
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached face clustering)')
                return ClusterData(episode_id=input_data.episode_id, episode_info=input_data.episode_info, path=output_path)
        context.logger.info(f'Clustering faces for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)
        context.mark_step_completed(self.name, input_data.episode_id)
        return ClusterData(episode_id=input_data.episode_id, episode_info=input_data.episode_info, path=output_path)
