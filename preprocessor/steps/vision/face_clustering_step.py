from pathlib import Path
from typing import List

from preprocessor.config.step_configs import FaceClusteringConfig
from preprocessor.core.artifacts import (
    ClusterData,
    FrameCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    JsonFileOutput,
    OutputDescriptor,
)


class FaceClusteringStep(PipelineStep[FrameCollection, ClusterData, FaceClusteringConfig]):
    def get_output_descriptors(self) -> List[OutputDescriptor]:
        """Define output file descriptors for face clustering step."""
        return [
            JsonFileOutput(
                subdir="clusters/faces",
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ]


    def __init__(self, config: FaceClusteringConfig) -> None:
        super().__init__(config)
        self.__model = None

    @property
    def name(self) -> str:
        return 'face_clustering'

    def cleanup(self) -> None:
        self.__model = None

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__model is None:
            context.logger.info('Loading Face Clustering model...')

    def execute_batch(
        self, input_data: List[FrameCollection], context: ExecutionContext,
    ) -> List[ClusterData]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.__execute_single,
        )

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__model:
            context.logger.info('Face Clustering model unloaded')
            self.__model = None

    def __execute_single(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ClusterData:
        """Execute single episode (batch processing variant without lazy loading)."""
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached face clustering'):
            return self.__construct_cluster_data(input_data, output_path)

        context.logger.info(f'Clustering faces for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_cluster_data(input_data, output_path)

    def execute(
            self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ClusterData:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached face clustering'):
            return self.__construct_cluster_data(input_data, output_path)

        context.logger.info(f'Clustering faces for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_cluster_data(input_data, output_path)

    def __resolve_output_path(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            {
                'season': f'S{input_data.episode_info.season:02d}',
                'episode': input_data.episode_info.episode_code(),
            },
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
