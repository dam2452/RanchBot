from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from insightface.app import FaceAnalysis
import numpy as np

from preprocessor.lib.characters.face_detection import FaceDetector


def process_frames_for_detection(
    frame_files: List[Path],
    face_app: FaceAnalysis,
    character_vectors: Dict[str, np.ndarray],
    threshold: float,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for frame_path in frame_files:
        detections: List[Dict[str, Any]] = FaceDetector.detect_characters_in_frame(
            frame_path,
            face_app,
            character_vectors,
            threshold,
        )
        if detections:
            results.append({'frame': frame_path.name, 'faces': detections})
    return results
