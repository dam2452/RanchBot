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
from preprocessor.services.io.detection_io import process_frames_for_detection
from preprocessor.services.io.files import (
    atomic_write_json,
    load_json,
)


class CharacterDetectorStep(PipelineStep[FrameCollection, DetectionResults, CharacterDetectionConfig]):

    def __init__(self, config: CharacterDetectionConfig) -> None:
        super().__init__(config)
        self._face_app = None
        self._character_vectors: Dict[str, np.ndarray] = {}

    def cleanup(self) -> None:
        self._face_app = None
        self._character_vectors = {}

    def execute(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> DetectionResults:
        output_path = self._get_output_path(input_data, context)

        if self._should_skip_processing(output_path, context, input_data):
            return self._load_cached_result(output_path, input_data)

        self._ensure_model_loaded(context)
        context.logger.info(f'Detecting characters in {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        frame_files = self._get_frame_files(input_data)
        if not frame_files:
            return self._create_empty_result(output_path, input_data, context)

        results = self._detect_characters(frame_files)
        self._save_results(results, output_path, input_data, context, frame_files)

        context.mark_step_completed(self.name, input_data.episode_id)
        return DetectionResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            detection_type='character',
            detection_count=len(results),
        )

    @property
    def name(self) -> str:
        return 'character_detection'

    @staticmethod
    def _get_output_path(input_data: FrameCollection, context: ExecutionContext) -> Path:
        filename = f'{context.series_name}_{input_data.episode_info.episode_code()}'
        output_filename: str = f'{filename}_character_detections.json'
        return context.get_output_path(
            input_data.episode_info, 'character_detections', output_filename,
        )

    def _should_skip_processing(
        self,
        output_path: Path,
        context: ExecutionContext,
        input_data: FrameCollection,
    ) -> bool:
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached character detections)')
                return True
        return False

    @staticmethod
    def _load_cached_result(output_path: Path, input_data: FrameCollection) -> DetectionResults:
        det_data: Dict[str, Any] = load_json(output_path)
        return DetectionResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            detection_type='character',
            detection_count=len(det_data.get('detections', [])),
        )

    def _ensure_model_loaded(self, context: ExecutionContext) -> None:
        if self._face_app is None:
            context.logger.info('Initializing face detection model...')
            self._face_app = FaceDetector.init()
            self._load_character_references(context)

    def _load_character_references(self, context: ExecutionContext) -> None:
        characters_dir: Path = Path('preprocessor/output_data') / context.series_name / 'characters'
        if not characters_dir.exists():
            characters_dir = Path('preprocessor/input_data') / context.series_name / 'characters'

        if characters_dir.exists():
            context.logger.info(f'Loading character references from {characters_dir}')
            self._character_vectors = FaceDetector.load_character_references(
                characters_dir, self._face_app,
            )
        else:
            context.logger.warning(f'Characters directory not found: {characters_dir}')

    @staticmethod
    def _get_frame_files(input_data: FrameCollection) -> List[Path]:
        return sorted([
            f for f in input_data.directory.glob('*.jpg')
            if f.is_file() and 'frame_' in f.name
        ])

    @staticmethod
    def _create_empty_result(
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

    def _detect_characters(self, frame_files: List[Path]) -> List[Dict[str, Any]]:
        return process_frames_for_detection(
            frame_files, self._face_app, self._character_vectors, self.config.threshold,
        )

    def _save_results(
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
        atomic_write_json(output_path, output_data)

    @staticmethod
    def __count_characters(results: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for res in results:
            for face in res.get('faces', []):
                name: str = face.get('character_name', 'unknown')
                counts[name] = counts.get(name, 0) + 1
        return counts
