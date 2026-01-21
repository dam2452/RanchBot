from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)

from hsemotion_onnx.facial_emotions import HSEmotionRecognizer
import numpy as np

from preprocessor.config.config import settings
from preprocessor.utils.console import console

EMOTION_LABELS = [
    'anger',
    'contempt',
    'disgust',
    'fear',
    'happiness',
    'neutral',
    'sadness',
    'surprise',
]


def init_emotion_model() -> HSEmotionRecognizer:
    model_name = settings.emotion_detection.model_name

    console.print(f"[cyan]Loading HSEmotion model: {model_name}...[/cyan]")

    try:
        fer = HSEmotionRecognizer(model_name=model_name)
        console.print(f"[green]✓ HSEmotion model loaded: {model_name}[/green]")
        return fer
    except Exception as e:
        raise RuntimeError(f"Failed to load HSEmotion model {model_name}: {e}") from e


def detect_emotion(
    face_image: np.ndarray,
    model: HSEmotionRecognizer,
) -> Tuple[str, float, Dict[str, float]]:
    try:
        emotion, scores = model.predict_emotions(face_image, logits=False)

        emotion_scores = {
            EMOTION_LABELS[i]: float(scores[i])
            for i in range(len(EMOTION_LABELS))
        }

        confidence = float(max(scores))
        dominant_emotion = emotion.lower()

        return dominant_emotion, confidence, emotion_scores

    except Exception as e:
        raise RuntimeError(f"Emotion detection failed: {e}") from e


def crop_face_from_frame(frame: np.ndarray, bbox: Dict[str, int]) -> Optional[np.ndarray]:
    try:
        x1, y1 = bbox['x1'], bbox['y1']
        x2, y2 = bbox['x2'], bbox['y2']

        if x1 < 0 or y1 < 0 or x2 > frame.shape[1] or y2 > frame.shape[0]:
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(frame.shape[1], x2)
            y2 = min(frame.shape[0], y2)

        if x2 <= x1 or y2 <= y1:
            return None

        face_crop = frame[y1:y2, x1:x2]

        if face_crop.size == 0:
            return None

        return face_crop

    except Exception: # pylint: disable=broad-exception-caught
        return None


def detect_emotions_batch(
    face_images: List[np.ndarray],
    model: HSEmotionRecognizer,
) -> List[Tuple[str, float, Dict[str, float]]]:
    results = []

    try:
        batch_results = model.predict_multi_emotions(face_images, logits=False)

        for emotion, scores in batch_results:
            emotion_scores = {
                EMOTION_LABELS[i]: float(scores[i])
                for i in range(len(EMOTION_LABELS))
            }
            confidence = float(max(scores))
            dominant_emotion = emotion.lower()

            results.append((dominant_emotion, confidence, emotion_scores))

    except Exception: # pylint: disable=broad-exception-caught
        for face_img in face_images:
            try:
                emotion, scores = model.predict_emotions(face_img, logits=False)
                emotion_scores = {
                    EMOTION_LABELS[i]: float(scores[i])
                    for i in range(len(EMOTION_LABELS))
                }
                confidence = float(max(scores))
                dominant_emotion = emotion.lower()
                results.append((dominant_emotion, confidence, emotion_scores))
            except Exception: # pylint: disable=broad-exception-caught
                results.append(None)

    return results
