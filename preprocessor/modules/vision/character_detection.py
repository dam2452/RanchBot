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
from preprocessor.lib.characters import FaceDetector
from preprocessor.lib.io.detection_io import process_frames_for_detection
from preprocessor.lib.io.files import (
    atomic_write_json,
    load_json,
)


class CharacterDetectorStep(PipelineStep[FrameCollection, DetectionResults, CharacterDetectionConfig]):

    def __init__(self, config: CharacterDetectionConfig) -> None:
        super().__init__(config)
        self._face_app = None
        self._character_vectors: Dict[str, np.ndarray] = {}

    @property
    def name(self) -> str:
        return 'character_detection'

    def execute(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> DetectionResults:
        filename = f'{context.series_name}_{input_data.episode_info.episode_code()}'
        output_filename: str = f'{filename}_character_detections.json'
        output_path: Path = context.get_output_path(
            input_data.episode_info, 'character_detections', output_filename,
        )
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached character detections)')
                det_data: Dict[str, Any] = load_json(output_path)
                return DetectionResults(
                    episode_id=input_data.episode_id,
                    episode_info=input_data.episode_info,
                    path=output_path,
                    detection_type='character',
                    detection_count=len(det_data.get('detections', [])),
                )
        if self._face_app is None:
            context.logger.info('Initializing face detection model...')
            self._face_app = FaceDetector.init()
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
        context.logger.info(f'Detecting characters in {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)
        frame_files: List[Path] = sorted([
            f for f in input_data.directory.glob('*.jpg')
            if f.is_file() and 'frame_' in f.name
        ])
        if not frame_files:
            context.logger.warning(f'No frame files found in {input_data.directory}')
            return DetectionResults(
                episode_id=input_data.episode_id,
                episode_info=input_data.episode_info,
                path=output_path,
                detection_type='character',
                detection_count=0,
            )
        results: List[Dict[str, Any]] = process_frames_for_detection(
            frame_files, self._face_app, self._character_vectors, self.config.threshold,
        )
        output_data: Dict[str, Any] = {
            'episode_id': input_data.episode_id,
            'series_name': context.series_name,
            'detection_settings': self.config.dict(),
            'statistics': {
                'total_frames_processed': len(frame_files),
                'frames_with_detections': len(results),
                'character_counts': self._count_characters(results),
            },
            'detections': results,
        }
        atomic_write_json(output_path, output_data)
        context.mark_step_completed(self.name, input_data.episode_id)
        return DetectionResults(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            detection_type='character',
            detection_count=len(results),
        )

    @staticmethod
    def _count_characters(results: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for res in results:
            for face in res.get('faces', []):
                name: str = face.get('character_name', 'unknown')
                counts[name] = counts.get(name, 0) + 1
        return counts

    def cleanup(self) -> None:
        self._face_app = None
        self._character_vectors = {}
