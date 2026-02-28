# pylint: disable=duplicate-code
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

import numpy as np

from preprocessor.config.output_paths import get_base_output_dir
from preprocessor.config.step_configs import CharacterDetectionConfig
from preprocessor.core.artifacts import (
    DetectionResults,
    FrameCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    JsonFileOutput,
    OutputDescriptor,
)
from preprocessor.services.characters import FaceDetector
from preprocessor.services.io.files import FileOperations


class CharacterDetectorStep(PipelineStep[FrameCollection, DetectionResults, CharacterDetectionConfig]):
    def __init__(self, config: CharacterDetectionConfig) -> None:
        super().__init__(config)
        self.__face_app = None
        self.__character_vectors: Dict[str, np.ndarray] = {}

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__face_app is None:
            context.logger.info('Loading Face Detection model...')
            self.__face_app = FaceDetector.init()
            self.__load_character_references(context)

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__face_app:
            context.logger.info('Face Detection model unloaded')
            self.__face_app = None
            self.__character_vectors = {}

    def cleanup(self) -> None:
        self.__face_app = None
        self.__character_vectors = {}

    def execute_batch(
        self, input_data: List[FrameCollection], context: ExecutionContext,
    ) -> List[DetectionResults]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> DetectionResults:
        output_path = self._get_cache_path(input_data, context)
        self.__prepare_detection_environment(context)

        frame_files = self.__extract_frame_files(input_data)
        if not frame_files:
            return self.__construct_empty_result(output_path, input_data, context)

        results = self.__process_character_detection(frame_files)
        self.__save_detection_results(
            results, output_path, input_data, context, frame_files,
        )

        return DetectionResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            detection_type='character',
            detection_count=len(results),
        )

    def get_output_descriptors(self) -> List[OutputDescriptor]:
        """Define output file descriptors for character detection step."""
        return [
            JsonFileOutput(
                subdir="detections/characters",
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ]

    def _get_cache_path(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            self.__create_path_variables(input_data),
        )

    def _load_from_cache(
        self, cache_path: Path, input_data: FrameCollection, context: ExecutionContext,
    ) -> DetectionResults:
        detection_data: Dict[str, Any] = FileOperations.load_json(cache_path)
        return DetectionResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=cache_path,
            detection_type='character',
            detection_count=len(detection_data.get('detections', [])),
        )

    def __prepare_detection_environment(self, context: ExecutionContext) -> None:
        if self.__face_app is None:
            context.logger.info('Initializing face detection model...')
            self.__face_app = FaceDetector.init()
            self.__load_character_references(context)

    def __load_character_references(self, context: ExecutionContext) -> None:
        base_dir = get_base_output_dir(context.series_name)
        characters_dir: Path = base_dir / 'character_references_processed'
        if not characters_dir.exists():
            characters_dir = base_dir / 'character_faces'

        if characters_dir.exists():
            context.logger.info(f'Loading character references from {characters_dir}')
            self.__character_vectors = FaceDetector.load_character_references(
                characters_dir, self.__face_app,
            )
        else:
            context.logger.warning(f'Characters directory not found: {characters_dir}')

    def __process_character_detection(
        self, frame_files: List[Path],
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for frame_path in frame_files:
            detections: List[Dict[str, Any]] = FaceDetector.detect_characters_in_frame(
                frame_path,
                self.__face_app,
                self.__character_vectors,
                self.config.threshold,
            )
            if detections:
                results.append({'frame': frame_path.name, 'faces': detections})
        return results

    def __save_detection_results(
        self,
        results: List[Dict[str, Any]],
        output_path: Path,
        input_data: FrameCollection,
        context: ExecutionContext,
        frame_files: List[Path],
    ) -> None:
        output_data: Dict[str, Any] = {
            'episode_id': input_data.episode_id,
            'series_name': context.series_name,
            'detection_settings': self.config.model_dump(),
            'statistics': {
                'total_frames_processed': len(frame_files),
                'frames_with_detections': len(results),
                'character_counts': self.__count_characters(results),
            },
            'detections': results,
        }
        FileOperations.atomic_write_json(output_path, output_data)

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

    @staticmethod
    def __construct_empty_result(
        output_path: Path,
        input_data: FrameCollection,
        context: ExecutionContext,
    ) -> DetectionResults:
        context.logger.warning(f'No frame files found in {input_data.directory}')
        return DetectionResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            detection_type='character',
            detection_count=0,
        )

    @staticmethod
    def __count_characters(results: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for res in results:
            for face in res.get('faces', []):
                name: str = face.get('name', 'unknown')
                counts[name] = counts.get(name, 0) + 1
        return counts
