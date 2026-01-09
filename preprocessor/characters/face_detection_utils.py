from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import cv2
from insightface.app import FaceAnalysis
import numpy as np
from numpy.linalg import norm

from preprocessor.utils.console import console


def load_character_references(
    characters_dir: Path,
    face_app: FaceAnalysis,
) -> Dict[str, np.ndarray]:
    console.print("[blue]Loading character references...[/blue]")
    character_vectors = {}

    for char_dir in characters_dir.iterdir():
        if not char_dir.is_dir():
            continue

        char_name = char_dir.name.replace("_", " ").title()
        images = list(char_dir.glob("*.jpg"))

        if not images:
            continue

        embeddings = []
        for img_path in images:
            emb = get_face_embedding(str(img_path), face_app)
            if emb is not None:
                embeddings.append(emb)

        if embeddings:
            mean_emb = np.mean(embeddings, axis=0)
            centroid = mean_emb / norm(mean_emb)
            character_vectors[char_name] = centroid
            console.print(f"[green]  ✓ {char_name}: {len(embeddings)} reference images[/green]")

    console.print(f"[green]✓ Loaded {len(character_vectors)} characters[/green]")
    return character_vectors


def get_face_embedding(img_path: str, face_app: FaceAnalysis) -> Optional[np.ndarray]:
    img = cv2.imread(img_path)
    if img is None:
        return None

    faces = face_app.get(img)
    if not faces:
        return None

    faces.sort(key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
    return faces[0].normed_embedding


def detect_characters_in_frame(
    frame_path: Path,
    face_app: FaceAnalysis,
    character_vectors: Dict[str, np.ndarray],
    threshold: float,
) -> List[Dict[str, Any]]:
    img = cv2.imread(str(frame_path))
    if img is None:
        return []

    faces = face_app.get(img)
    if not faces:
        return []

    detected = []

    for face in faces:
        face_embedding = face.normed_embedding

        for char_name, char_vector in character_vectors.items():
            similarity = np.dot(face_embedding, char_vector)

            if similarity > threshold:
                detected.append({
                    "name": char_name,
                    "confidence": float(similarity),
                })

    detected.sort(key=lambda x: x["confidence"], reverse=True)
    return detected
