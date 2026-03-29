from datetime import datetime
import json
from pathlib import Path
from typing import (
    List,
    Tuple,
)

from insightface.app import FaceAnalysis
import numpy as np

from preprocessor.config.output_paths import get_base_output_dir
from preprocessor.config.settings_instance import settings
from preprocessor.config.step_configs import CharacterReferenceProcessorConfig
from preprocessor.core.artifacts import SourceVideo
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    DirectoryOutput,
    OutputDescriptor,
)
from preprocessor.services.characters import (
    FaceClusterer,
    FaceDetector,
)
from preprocessor.services.characters.cluster_folder_manager import ClusterFolderManager
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
        if self.config.reference_source == "clusters":
            return self.__process_from_clusters(input_data, context)
        return self.__process_from_web(input_data, context)

    @staticmethod
    def __resolve_paths(context: ExecutionContext) -> Tuple[Path, Path]:
        base_dir = get_base_output_dir(context.series_name)
        return base_dir / 'character_faces', base_dir / 'character_references_processed'

    def __process_from_web(
        self,
        input_data: SourceVideo,
        context: ExecutionContext,
    ) -> SourceVideo:
        characters_dir, output_dir = self.__resolve_paths(context)
        self.__validate_web_input_directory(characters_dir)
        self.__run_reference_processor(characters_dir, output_dir, context)
        return input_data

    def __process_from_clusters(
        self,
        input_data: SourceVideo,
        context: ExecutionContext,
    ) -> SourceVideo:
        cluster_dir = context.base_output_dir / 'character_clusters'
        _, output_dir = self.__resolve_paths(context)

        character_names = self.__load_character_names(context)
        is_complete, missing = ClusterFolderManager.is_complete(cluster_dir, character_names)

        if not is_complete:
            context.logger.warning(
                f"Cluster labeling incomplete. Missing characters: {missing}",
            )
            raise RuntimeError(
                f"Not all characters have labeled cluster folders. Missing: {missing}",
            )

        labeled_folders = ClusterFolderManager.get_labeled_folders(cluster_dir)
        context.logger.info(
            f"Processing {len(labeled_folders)} labeled cluster folders into face vectors...",
        )

        face_app = None
        try:
            face_app = FaceDetector.init()
            for char_name, folder in labeled_folders.items():
                self.__process_cluster_character(
                    char_name, folder, output_dir, face_app, context,
                )
        finally:
            if face_app is not None:
                FaceClusterer.cleanup_gpu_memory()

        context.logger.info(f"Cluster-based face vectors saved to: {output_dir}")
        return input_data

    def __process_cluster_character(
        self,
        char_name: str,
        cluster_folder: Path,
        output_dir: Path,
        face_app: FaceAnalysis,
        context: ExecutionContext,
    ) -> None:
        vector = ClusterFolderManager.extract_face_vector(
            cluster_folder, face_app, context.logger,
        )
        if vector is None:
            context.logger.warning(f"Could not extract face vector for '{char_name}', skipping")
            return

        char_out = output_dir / char_name
        char_out.mkdir(parents=True, exist_ok=True)
        np.save(char_out / 'face_vector.npy', vector)
        self.__save_cluster_metadata(char_out, char_name, cluster_folder, vector)
        context.logger.info(f"Saved face vector for '{char_name}'")

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
    def __load_character_names(context: ExecutionContext) -> List[str]:
        characters_json = context.base_output_dir / f'{context.series_name}_characters.json'
        if not characters_json.exists():
            raise FileNotFoundError(
                f"Characters JSON not found: {characters_json}. "
                f"Run characters_metadata step first.",
            )
        with open(characters_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [c['name'] for c in data.get('characters', []) if c.get('name')]

    @staticmethod
    def __save_cluster_metadata(
        char_out: Path,
        char_name: str,
        cluster_folder: Path,
        vector: np.ndarray,
    ) -> None:
        metadata = {
            'character_name': char_name,
            'source': 'clusters',
            'cluster_folder': str(cluster_folder),
            'processed_at': datetime.now().isoformat(),
            'face_vector_dim': int(vector.shape[0]),
            'processing_params': {
                'face_model': settings.face_recognition.model_name,
            },
        }
        with open(char_out / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    @staticmethod
    def __validate_web_input_directory(characters_dir: Path) -> None:
        if not characters_dir.exists():
            raise FileNotFoundError(
                f"Character faces directory not found: {characters_dir}. "
                f"Run character_reference step first.",
            )

    def _check_cache_validity(
        self,
        output_path: Path,
        context: ExecutionContext,
        episode_id: str,
        cache_description: str,
    ) -> bool:
        if output_path.exists() and not context.force_rerun:
            vectors = list(output_path.rglob('face_vector.npy'))
            if vectors:
                if not context.is_step_completed(self.name, episode_id):
                    context.mark_step_completed(self.name, episode_id)
                context.logger.info(
                    f'Skipping {episode_id} ({cache_description}, {len(vectors)} vectors found)',
                )
                return True
        return False
