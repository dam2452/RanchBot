from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np


@dataclass
class FaceData:
    bbox: np.ndarray
    face_img: np.ndarray
    face_vector: np.ndarray
    source_image_idx: int
    source_image_path: Path

@dataclass
class CandidateFace:
    avg_similarity: float
    faces: List[FaceData]
