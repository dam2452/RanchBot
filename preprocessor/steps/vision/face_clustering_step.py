# pylint: disable=duplicate-code
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from insightface.app import FaceAnalysis

from preprocessor.config.settings_instance import settings
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
from preprocessor.services.characters import FaceDetector
from preprocessor.services.characters.face_clusterer import FaceClusterer
from preprocessor.services.io.files import FileOperations


class FaceClusteringStep(PipelineStep[FrameCollection, ClusterData, FaceClusteringConfig]):
    def __init__(self, config: FaceClusteringConfig) -> None:
        super().__init__(config)
        self.__face_app: Optional[FaceAnalysis] = None

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__face_app is None:
            context.logger.info('Loading Face Clustering model...')
            self.__face_app = FaceDetector.init()

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__face_app:
            context.logger.info('Face Clustering model unloaded')
            self.__face_app = None
            FaceClusterer.cleanup_gpu_memory()

    def cleanup(self) -> None:
        self.__face_app = None

    def execute_batch(
            self, input_data: List[FrameCollection], context: ExecutionContext,
    ) -> List[ClusterData]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
            self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ClusterData:
        output_path = self._get_cache_path(input_data, context)
        face_app = self.__face_app

        frame_files = self.__extract_frame_files(input_data)
        if not frame_files:
            context.logger.warning(f'No frame files found in {input_data.directory}')
            self.__write_empty_output(output_path, input_data, context)
            return self.__build_result(input_data, output_path)

        face_data = FaceClusterer.extract_face_embeddings(frame_files, face_app)
        if not face_data:
            context.logger.warning(f'No faces detected in episode {input_data.episode_id}')
            self.__write_empty_output(output_path, input_data, context)
            return self.__build_result(input_data, output_path)

        clustering = settings.face_clustering
        labels = FaceClusterer.cluster_embeddings(
            face_data, clustering.min_cluster_size, clustering.min_samples,
        )

        output_data = FaceClusterer.build_cluster_output(
            face_data=face_data,
            labels=labels,
            save_noise=clustering.save_noise,
            episode_id=input_data.episode_id,
            series_name=context.series_name,
            min_cluster_size=clustering.min_cluster_size,
            min_samples=clustering.min_samples,
            model_name=settings.face_recognition.model_name,
            total_frames=len(frame_files),
        )
        FileOperations.atomic_write_json(output_path, output_data)

        return self.__build_result(input_data, output_path)

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        return [
            JsonFileOutput(
                subdir='clusters/faces',
                pattern='{season}/{episode}.json',
                min_size_bytes=10,
            ),
        ]

    def _get_cache_path(
            self, input_data: FrameCollection, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0, context, self.__create_path_variables(input_data),
        )

    def _load_from_cache(
            self, cache_path: Path, input_data: FrameCollection, context: ExecutionContext,
    ) -> ClusterData:
        return self.__build_result(input_data, cache_path)

    def __write_empty_output(
            self,
            output_path: Path,
            input_data: FrameCollection,
            context: ExecutionContext,
    ) -> None:
        empty_data: Dict[str, Any] = {
            'episode_id': input_data.episode_id,
            'series_name': context.series_name,
            'statistics': {
                'total_faces_detected': 0,
                'total_clusters': 0,
                'noise_faces': 0,
                'frames_processed': 0,
                'frames_with_faces': 0,
            },
            'clusters': {},
            'noise': {},
        }
        FileOperations.atomic_write_json(output_path, empty_data)

    @staticmethod
    def __build_result(input_data: FrameCollection, output_path: Path) -> ClusterData:
        return ClusterData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
        )

    @staticmethod
    def __create_path_variables(input_data: FrameCollection) -> Dict[str, str]:
        return {
            'season': f'S{input_data.episode_info.season:02d}',
            'episode': input_data.episode_info.episode_code(),
        }

    @staticmethod
    def __extract_frame_files(input_data: FrameCollection) -> List[Path]:
        return sorted([
            f for f in input_data.directory.glob('*.jpg')
            if f.is_file() and 'frame_' in f.name
        ])
