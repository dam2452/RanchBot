from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import cv2
from hsemotion_onnx.facial_emotions import HSEmotionRecognizer
import numpy as np

from preprocessor.config.step_configs import EmotionDetectionConfig
from preprocessor.core.artifacts import (
    EmotionData,
    FrameCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.io.files import FileOperations
from preprocessor.services.video.emotion_utils import EmotionDetector


class EmotionDetectionStep(PipelineStep[FrameCollection, EmotionData, EmotionDetectionConfig]):

    def __init__(self, config: EmotionDetectionConfig) -> None:
        super().__init__(config)
        self._model: Optional[HSEmotionRecognizer] = None

    def cleanup(self) -> None:
        self._model = None

    def execute(self, input_data: FrameCollection, context: ExecutionContext) -> EmotionData:
        detections_path = self._get_character_detections_path(input_data, context)

        if self._check_cache_validity(detections_path, context, input_data.episode_id, 'cached emotion detection'):
            return EmotionData(
                episode_id=input_data.episode_id,
                episode_info=input_data.episode_info,
                path=detections_path,
            )

        if not detections_path.exists():
            context.logger.warning(
                f'No character detections found for emotion analysis: {detections_path}',
            )
            return EmotionData(
                episode_id=input_data.episode_id,
                episode_info=input_data.episode_info,
                path=detections_path,
            )

        context.logger.info(f'Detecting emotions for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        self._ensure_model_loaded(context)

        detections_data = FileOperations.load_json(detections_path)
        self._process_emotions(detections_data, input_data, context)
        FileOperations.atomic_write_json(detections_path, detections_data)

        context.mark_step_completed(self.name, input_data.episode_id)
        return EmotionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=detections_path,
        )

    @property
    def name(self) -> str:
        return 'emotion_detection'

    @staticmethod
    def _get_character_detections_path(
        input_data: FrameCollection, context: ExecutionContext,
    ) -> Path:
        filename = f'{context.series_name}_{input_data.episode_info.episode_code()}'
        output_filename: str = f'{filename}_character_detections.json'
        return context.get_output_path(
            input_data.episode_info, 'character_detections', output_filename,
        )

    def _ensure_model_loaded(self, context: ExecutionContext) -> None:
        if self._model is None:
            self._model = EmotionDetector._init_model(context.logger)

    def _process_emotions(
        self,
        detections_data: Dict[str, Any],
        input_data: FrameCollection,
        context: ExecutionContext,
    ) -> None:
        detections: List[Dict[str, Any]] = detections_data.get('detections', [])

        face_crops, face_metadata = self._collect_face_crops(
            detections, input_data.directory, context,
        )

        if not face_crops:
            context.logger.warning('No valid face crops found for emotion detection')
            return

        context.logger.info(f'Processing {len(face_crops)} faces with HSEmotion model')
        emotion_results = EmotionDetector._detect_batch(
            face_crops, self._model, batch_size=32, logger=context.logger,
        )

        self._apply_emotion_results(detections, emotion_results, face_metadata, context)

    @staticmethod
    def _collect_face_crops(
        detections: List[Dict[str, Any]],
        frames_dir: Path,
        context: ExecutionContext,
    ) -> Tuple[List[np.ndarray], List[Dict[str, int]]]:
        face_crops: List[np.ndarray] = []
        face_metadata: List[Dict[str, int]] = []

        total_faces = sum(len(d.get('faces', [])) for d in detections)
        context.logger.info(f'Collecting {total_faces} faces for batch emotion analysis')

        for detection_idx, detection in enumerate(detections):
            frame_file = detection.get('frame_file')
            if not frame_file:
                continue

            frame_path = frames_dir / frame_file
            if not frame_path.exists():
                continue

            frame = cv2.imread(str(frame_path))
            if frame is None:
                continue

            faces = detection.get('faces', [])
            for face_idx, face in enumerate(faces):
                bbox = face.get('bbox')
                if not bbox:
                    continue

                face_crop = EmotionDetector._crop_face(frame, bbox)
                if face_crop is None:
                    continue

                face_crops.append(face_crop)
                face_metadata.append({
                    'detection_idx': detection_idx,
                    'face_idx': face_idx,
                })

        return face_crops, face_metadata

    @staticmethod
    def _apply_emotion_results(
        detections: List[Dict[str, Any]],
        emotion_results: List[Optional[Tuple[str, float, Dict[str, float]]]],
        face_metadata: List[Dict[str, int]],
        context: ExecutionContext,
    ) -> None:
        processed = 0
        for result, metadata in zip(emotion_results, face_metadata):
            if result is None:
                continue

            dominant_emotion, confidence, emotion_scores = result
            detection_idx = metadata['detection_idx']
            face_idx = metadata['face_idx']

            face = detections[detection_idx]['faces'][face_idx]
            face['emotion'] = {
                'label': dominant_emotion,
                'confidence': confidence,
                'scores': emotion_scores,
            }
            processed += 1

        total = len(face_metadata)
        context.logger.info(f'Emotion analysis complete: {processed}/{total} faces processed')
