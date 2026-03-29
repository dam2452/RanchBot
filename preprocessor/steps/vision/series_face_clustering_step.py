from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.settings_instance import settings
from preprocessor.config.step_configs import SeriesFaceClusteringConfig
from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    JsonFileOutput,
    OutputDescriptor,
)
from preprocessor.services.characters import (
    FaceClusterer,
    FaceDetector,
)
from preprocessor.services.characters.cluster_folder_manager import ClusterFolderManager
from preprocessor.services.io.files import FileOperations


class SeriesFaceClusteringStep(PipelineStep[SourceVideo, SourceVideo, SeriesFaceClusteringConfig]):
    @property
    def is_global(self) -> bool:
        return True

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        return [
            JsonFileOutput(
                pattern='_cluster_index.json',
                subdir='character_clusters',
                min_size_bytes=10,
            ),
        ]

    def _get_cache_path(self, input_data: SourceVideo, context: ExecutionContext) -> Path:
        return context.base_output_dir / 'character_clusters' / '_cluster_index.json'

    def _load_from_cache(
        self, cache_path: Path, input_data: SourceVideo, context: ExecutionContext,
    ) -> SourceVideo:
        context.logger.info(f"Series character clusters already exist: {cache_path.parent}")
        return input_data

    def _process(self, input_data: SourceVideo, context: ExecutionContext) -> SourceVideo:
        frames_root = context.base_output_dir / 'frames'
        output_dir = context.base_output_dir / 'character_clusters'

        frame_files = self.__collect_frame_files(frames_root)
        if not frame_files:
            context.logger.warning(f"No frames found in {frames_root}")
            return input_data

        context.logger.info(
            f"Extracting face embeddings from {len(frame_files)} frames across the series...",
        )

        clustering = settings.face_clustering
        face_app = None
        try:
            face_app = FaceDetector.init(det_thresh=clustering.min_det_score)
            face_data = FaceClusterer.extract_face_embeddings(
                frame_files, face_app, self.config.prefetch_workers,
                min_det_score=clustering.min_det_score,
                min_face_px=clustering.min_face_px,
            )

            if not face_data:
                context.logger.warning("No faces detected across the series")
                return input_data

            context.logger.info(f"Clustering {len(face_data)} face embeddings series-wide...")

            labels = FaceClusterer.cluster_embeddings(
                face_data, clustering.min_cluster_size, clustering.min_samples,
            )

            cluster_count = ClusterFolderManager.create_cluster_folders(
                face_data=face_data,
                labels=labels,
                output_dir=output_dir,
                logger=context.logger,
            )

            self.__write_cluster_index(output_dir, context.series_name, cluster_count, face_data, frame_files)

            context.logger.info(
                f"Series clustering complete: {cluster_count} clusters → {output_dir}",
            )
        finally:
            if face_app is not None:
                FaceClusterer.cleanup_gpu_memory()

        return input_data

    @staticmethod
    def __write_cluster_index(
        output_dir: Path,
        series_name: str,
        cluster_count: int,
        face_data: List[Dict[str, Any]],
        frame_files: List[Path],
    ) -> None:
        index_data = {
            'series_name': series_name,
            'cluster_count': cluster_count,
            'total_faces': len(face_data),
            'total_frames': len(frame_files),
        }
        FileOperations.atomic_write_json(output_dir / '_cluster_index.json', index_data)

    @staticmethod
    def __collect_frame_files(frames_root: Path) -> List[Path]:
        if not frames_root.exists():
            return []
        return sorted([
            f for f in frames_root.rglob('*.jpg')
            if f.is_file() and 'frame_' in f.name
        ])
