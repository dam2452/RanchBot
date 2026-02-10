from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class FaceData:
    bbox: np.ndarray
    face_vector: np.ndarray
    source_image_path: Path
    source_image_idx: int
    face_img: np.ndarray

@dataclass
class CandidateFace:
    faces: list[FaceData]
    avg_similarity: float
