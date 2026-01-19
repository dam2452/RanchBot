from pathlib import Path
from typing import (
    Dict,
    Optional,
    Tuple,
)
import urllib.request

import cv2
import numpy as np
import onnxruntime as ort

from preprocessor.utils.console import console

EMOTION_LABELS = [
    'neutral',
    'happiness',
    'surprise',
    'sadness',
    'anger',
    'disgust',
    'fear',
    'contempt'
]


def download_ferplus_model(cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / "emotion_ferplus.onnx"

    if model_path.exists():
        return model_path

    url = 'https://github.com/onnx/models/raw/main/validated/vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx'

    console.print("[cyan]Downloading FER+ emotion model...[/cyan]")
    try:
        urllib.request.urlretrieve(url, str(model_path))
        console.print(f"[green]✓ Model downloaded to {model_path}[/green]")
        return model_path
    except Exception as e:
        raise RuntimeError(f"Failed to download FER+ model: {e}") from e


def init_emotion_model(model_path: Optional[Path] = None) -> ort.InferenceSession:
    if not ort.get_device() == 'GPU':
        available_providers = ort.get_available_providers()
        if 'CUDAExecutionProvider' not in available_providers:
            raise RuntimeError(
                "CUDA/GPU not available for ONNX Runtime. "
                "Emotion detection requires GPU. "
                f"Available providers: {available_providers}"
            )

    if model_path is None:
        from preprocessor.config.config import settings  # pylint: disable=import-outside-toplevel
        cache_dir = Path(settings.character.output_dir).parent / "emotion_model"
        model_path = download_ferplus_model(cache_dir)

    console.print(f"[cyan]Loading FER+ emotion model from {model_path}...[/cyan]")

    session = ort.InferenceSession(
        str(model_path),
        providers=['CUDAExecutionProvider']
    )

    console.print("[green]✓ FER+ emotion model loaded on GPU[/green]")
    return session


def softmax(x: np.ndarray) -> np.ndarray:
    exp_x = np.exp(x - np.max(x))
    return exp_x / exp_x.sum()


def preprocess_face_for_ferplus(face_image: np.ndarray) -> np.ndarray:
    if face_image is None or face_image.size == 0:
        raise ValueError("Empty face image")

    if len(face_image.shape) == 3:
        img_gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
    else:
        img_gray = face_image

    img_resized = cv2.resize(img_gray, (64, 64))

    img_input = img_resized.astype(np.float32)

    img_input = np.expand_dims(np.expand_dims(img_input, axis=0), axis=0)

    return img_input


def detect_emotion(
    face_image: np.ndarray,
    session: ort.InferenceSession
) -> Tuple[str, float, Dict[str, float]]:
    try:
        img_input = preprocess_face_for_ferplus(face_image)

        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: img_input})

        logits = outputs[0][0]

        probs = softmax(logits)

        emotion_scores = {
            EMOTION_LABELS[i]: float(probs[i])
            for i in range(len(EMOTION_LABELS))
        }

        dominant_idx = np.argmax(probs)
        dominant_emotion = EMOTION_LABELS[dominant_idx]
        confidence = float(probs[dominant_idx])

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

    except Exception:
        return None
