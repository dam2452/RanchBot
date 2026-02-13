from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

import numpy as np

from preprocessor.config.step_configs import CharacterDetectionConfig
from preprocessor.core.artifacts import (
    DetectionResults,
    FrameCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.characters import FaceDetector
from preprocessor.services.io.files import FileOperations


class CharacterDetectorStep(PipelineStep[FrameCollection, DetectionResults, CharacterDetectionConfig]):
    def __init__(self, config: CharacterDetectionConfig) -> None:
        super().__init__(config)
        self.__face_app = None
        self.__character_vectors: Dict[str, np.ndarray] = {}

    @property
    def name(self) -> str:
        return 'character_detection'

    def cleanup(self) -> None:
        self.__face_app = None
        self.__character_vectors = {}

    def execute(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> DetectionResults:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached character detections'):
            return self.__load_cached_result(output_path, input_data)

        self.__prepare_detection_environment(context)
        context.logger.info(f'Detecting characters in {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        frame_files = self.__extract_frame_files(input_data)
        if not frame_files:
            return self.__construct_empty_result(output_path, input_data, context)

        results = self.__process_character_detection(frame_files)
        self.__save_detection_results(results, output_path, input_data, context, frame_files)

        context.mark_step_completed(self.name, input_data.episode_id)
        return DetectionResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            detection_type='character',
            detection_count=len(results),
        )

    def __prepare_detection_environment(self, context: ExecutionContext) -> None:
        if self.__face_app is None:
            context.logger.info('Initializing face detection model...')
            self.__face_app = FaceDetector.init()
            self.__load_character_references(context)

    def __load_character_references(self, context: ExecutionContext) -> None:
        characters_dir: Path = Path('preprocessor/output_data') / context.series_name / 'characters'
        if not characters_dir.exists():
            characters_dir = Path('preprocessor/input_data') / context.series_name / 'characters'

        if characters_dir.exists():
            context.logger.info(f'Loading character references from {characters_dir}')
            self.__character_vectors = FaceDetector.load_character_references(
                characters_dir, self.__face_app,
            )
        else:
            context.logger.warning(f'Characters directory not found: {characters_dir}')

    def __process_character_detection(self, frame_files: List[Path]) -> List[Dict[str, Any]]:
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
            'detection_settings': self.config.dict(),
            'statistics': {
                'total_frames_processed': len(frame_files),
                'frames_with_detections': len(results),
                'character_counts': self.__count_characters(results),
            },
            'detections': results,
        }
        FileOperations.atomic_write_json(output_path, output_data)

    @staticmethod
    def __resolve_output_path(input_data: FrameCollection, context: ExecutionContext) -> Path:
        filename = f'{context.series_name}_{input_data.episode_info.episode_code()}'
        output_filename: str = f'{filename}_character_detections.json'
        return context.get_output_path(
            input_data.episode_info, 'character_detections', output_filename,
        )

    @staticmethod
    def __load_cached_result(output_path: Path, input_data: FrameCollection) -> DetectionResults:
        detection_data: Dict[str, Any] = FileOperations.load_json(output_path)
        return DetectionResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            detection_type='character',
            detection_count=len(detection_data.get('detections', [])),
        )

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
                name: str = face.get('character_name', 'unknown')
                counts[name] = counts.get(name, 0) + 1
        return counts
