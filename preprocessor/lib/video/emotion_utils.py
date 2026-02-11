from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)

from hsemotion_onnx.facial_emotions import HSEmotionRecognizer
import numpy as np

from preprocessor.config.config import settings
from preprocessor.lib.core.logging import ErrorHandlingLogger

EMOTION_LABELS = ['anger', 'contempt', 'disgust', 'fear', 'happiness', 'neutral', 'sadness', 'surprise']

class EmotionDetector:

    @staticmethod
    def detect(
        face_image: np.ndarray,
        model: HSEmotionRecognizer,
    ) -> Tuple[str, float, Dict[str, float]]:
        try:
            emotion, scores = model.predict_emotions(face_image, logits=False)
            return EmotionDetector.__process_emotion_result(emotion, scores)
        except Exception as e:
            raise RuntimeError(f'Emotion detection failed: {e}') from e

    @staticmethod
    def __clip_bbox(
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        width: int,
        height: int,
    ) -> Tuple[int, int, int, int]:
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(width, x2)
        y2 = min(height, y2)
        return (x1, y1, x2, y2)

    @staticmethod
    def __crop_face(frame: np.ndarray, bbox: Dict[str, int]) -> Optional[np.ndarray]: # pylint: disable=unused-private-member
        try:
            x1, y1, x2, y2 = (bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2'])
            height, width = frame.shape[:2]
            x1, y1, x2, y2 = EmotionDetector.__clip_bbox(x1, y1, x2, y2, width, height)
            if x2 <= x1 or y2 <= y1:
                return None
            face_crop = frame[y1:y2, x1:x2]
            return face_crop if face_crop.size > 0 else None
        except Exception:
            return None

    @staticmethod
    def __detect_batch( # pylint: disable=unused-private-member
        face_images: List[np.ndarray],
        model: HSEmotionRecognizer,
        batch_size: int = 32,
        logger: Optional[ErrorHandlingLogger] = None,
    ) -> List[Tuple[str, float, Dict[str, float]]]:
        results = []
        total = len(face_images)
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = face_images[batch_start:batch_end]
            progress_pct = int(batch_end / total * 100)
            if logger:
                logger.info(
                    f'Processing emotion batch {batch_start}-{batch_end}/{total} '
                    f'({progress_pct}%)',
                )
            try:
                batch_results = model.predict_multi_emotions(batch, logits=False)
                for emotion, scores in batch_results:
                    results.append(EmotionDetector.__process_emotion_result(emotion, scores))
            except Exception:
                for face_img in batch:
                    try:
                        emotion, scores = model.predict_emotions(face_img, logits=False)
                        results.append(EmotionDetector.__process_emotion_result(emotion, scores))
                    except Exception:
                        results.append(None)
        return results

    @staticmethod
    def __init_model(logger: Optional[ErrorHandlingLogger]=None) -> HSEmotionRecognizer: # pylint: disable=unused-private-member
        model_name = settings.emotion_detection.model_name
        if logger:
            logger.info(f'Loading HSEmotion model: {model_name}...')
        try:
            fer = HSEmotionRecognizer(model_name=model_name)
            if logger:
                logger.info(f'HSEmotion model loaded: {model_name}')
            return fer
        except Exception as e:
            raise RuntimeError(f'Failed to load HSEmotion model {model_name}: {e}') from e

    @staticmethod
    def __process_emotion_result(
        emotion: str,
        scores: np.ndarray,
    ) -> Tuple[str, float, Dict[str, float]]:
        emotion_scores = {
            EMOTION_LABELS[i]: float(scores[i])
            for i in range(len(EMOTION_LABELS))
        }
        confidence = float(max(scores))
        dominant_emotion = emotion.lower()
        return (dominant_emotion, confidence, emotion_scores)
