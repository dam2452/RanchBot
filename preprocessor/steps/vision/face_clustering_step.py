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

    def execute(
            self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ClusterData:
        output_path = self.__resolve_output_path(input_data, context)

        if self.__is_execution_cached(output_path, input_data.episode_id, context):
            context.logger.info(f'Skipping {input_data.episode_id} (cached face clustering)')
            return self.__construct_cluster_data(input_data, output_path)

        context.logger.info(f'Clustering faces for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_cluster_data(input_data, output_path)

    def __is_execution_cached(
            self, output_path: Path, episode_id: str, context: ExecutionContext,
    ) -> bool:
        if not output_path.exists():
            return False
        if context.force_rerun:
            return False
        return context.is_step_completed(self.name, episode_id)

    @staticmethod
    def __resolve_output_path(
            input_data: FrameCollection, context: ExecutionContext,
    ) -> Path:
        output_filename = f'{context.series_name}_{input_data.episode_info.episode_code()}_clusters.json'
        return context.get_output_path(
            input_data.episode_info, 'face_clusters', output_filename,
        )

    @staticmethod
    def __construct_cluster_data(
            input_data: FrameCollection, output_path: Path,
    ) -> ClusterData:
        return ClusterData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
        )
