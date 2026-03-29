from collections import defaultdict
import hashlib
from pathlib import Path
import shutil
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import cv2
from insightface.app import FaceAnalysis
import numpy as np

from preprocessor.services.core.logging import ErrorHandlingLogger


class ClusterFolderManager:
    @staticmethod
    def create_cluster_folders(
        face_data: List[Dict[str, Any]],
        labels: np.ndarray,
        output_dir: Path,
        logger: Optional[ErrorHandlingLogger] = None,
    ) -> int:
        groups: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for face_info, label in zip(face_data, labels):
            if int(label) == -1:
                continue
            groups[int(label)].append(face_info)

        sorted_clusters = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        for rank, (_, faces) in enumerate(sorted_clusters):
            cluster_dir = output_dir / str(rank)
            cluster_dir.mkdir(exist_ok=True)

            ranked_frames = ClusterFolderManager._rank_frames_by_centrality(faces)
            for frame_rank, (frame_path, _) in enumerate(ranked_frames):
                hash8 = hashlib.sha256(str(frame_path).encode()).hexdigest()[:8]
                dest_name = f"{frame_rank:04d}_{frame_path.stem}_{hash8}{frame_path.suffix}"
                dest_path = cluster_dir / dest_name
                if not dest_path.exists():
                    shutil.copy2(frame_path, dest_path)

        cluster_count = len(sorted_clusters)
        if logger:
            logger.info(f"Created {cluster_count} cluster folders in {output_dir}")
        return cluster_count

    @staticmethod
    def _rank_frames_by_centrality(
        faces: List[Dict[str, Any]],
    ) -> List[Tuple[Path, float]]:
        vectors = np.array([f['vector'] for f in faces])
        centroid = np.mean(vectors, axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 1e-6:
            centroid /= norm

        frame_max_sim: Dict[Path, float] = {}
        for face_info in faces:
            frame_path: Path = face_info['frame_path']
            sim = float(np.dot(face_info['vector'], centroid))
            if frame_path not in frame_max_sim or sim > frame_max_sim[frame_path]:
                frame_max_sim[frame_path] = sim

        return sorted(frame_max_sim.items(), key=lambda x: x[1], reverse=True)

    @staticmethod
    def get_labeled_folders(cluster_dir: Path) -> Dict[str, Path]:
        if not cluster_dir.exists():
            return {}
        return {
            d.name: d
            for d in sorted(cluster_dir.iterdir())
            if d.is_dir() and not d.name.isdigit()
        }

    @staticmethod
    def is_complete(
        cluster_dir: Path,
        character_names: List[str],
    ) -> Tuple[bool, List[str]]:
        labeled = ClusterFolderManager.get_labeled_folders(cluster_dir)
        normalized_labels = {ClusterFolderManager._normalize_name(n) for n in labeled}
        missing = [
            name for name in character_names
            if ClusterFolderManager._normalize_name(name) not in normalized_labels
        ]
        return len(missing) == 0, missing

    @staticmethod
    def extract_face_vector(
        cluster_folder: Path,
        face_app: FaceAnalysis,
        logger: Optional[ErrorHandlingLogger] = None,
    ) -> Optional[np.ndarray]:
        frame_files = sorted(cluster_folder.glob('*.jpg'))
        if not frame_files:
            if logger:
                logger.warning(f"No frames in {cluster_folder}")
            return None

        all_embeddings: List[np.ndarray] = []
        for frame_path in frame_files:
            img = cv2.imread(str(frame_path))
            if img is None:
                continue
            for face in face_app.get(img):
                all_embeddings.append(face.normed_embedding)

        if not all_embeddings:
            if logger:
                logger.warning(f"No faces detected in {cluster_folder}")
            return None

        vectors = np.array(all_embeddings)
        dominant = ClusterFolderManager._find_dominant_embedding(vectors)
        if dominant is None:
            return None

        norm = np.linalg.norm(dominant)
        if norm < 1e-6:
            return None
        return dominant / norm

    @staticmethod
    def _find_dominant_embedding(vectors: np.ndarray) -> Optional[np.ndarray]:
        if len(vectors) == 1:
            return vectors[0].copy()

        centroid = np.mean(vectors, axis=0)
        norm = np.linalg.norm(centroid)
        if norm < 1e-6:
            return None
        centroid = centroid / norm

        for _ in range(3):
            sims = vectors @ centroid
            threshold = float(np.percentile(sims, 30))
            mask = sims >= threshold
            if mask.sum() < 1:
                break
            centroid = np.mean(vectors[mask], axis=0)
            norm = np.linalg.norm(centroid)
            if norm < 1e-6:
                break
            centroid = centroid / norm

        return centroid

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.lower().replace(' ', '_').replace('-', '_')
