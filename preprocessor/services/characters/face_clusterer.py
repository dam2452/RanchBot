from collections import defaultdict
import gc
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Tuple,
)

from cuml.cluster import HDBSCAN as cuHDBSCAN
import cupy as cp
import cv2
from insightface.app import FaceAnalysis
import numpy as np
import torch


class FaceClusterer:
    @staticmethod
    def extract_face_embeddings(
            frame_files: List[Path],
            face_app: FaceAnalysis,
    ) -> List[Dict[str, Any]]:
        face_data: List[Dict[str, Any]] = []

        for frame_path in frame_files:
            img = cv2.imread(str(frame_path))  # pylint: disable=no-member
            if img is None:
                continue

            for face_idx, face in enumerate(face_app.get(img)):
                bbox = face.bbox.astype(int)
                x1 = max(0, bbox[0])
                y1 = max(0, bbox[1])
                x2 = min(img.shape[1], bbox[2])
                y2 = min(img.shape[0], bbox[3])

                if x2 <= x1 or y2 <= y1:
                    continue

                face_data.append({
                    'vector': face.normed_embedding,
                    'frame_path': frame_path,
                    'face_idx': face_idx,
                })

        return face_data

    @staticmethod
    def cluster_embeddings(
            face_data: List[Dict[str, Any]],
            min_cluster_size: int,
            min_samples: int,
    ) -> np.ndarray:
        vectors = np.array([fd['vector'] for fd in face_data])
        vectors_gpu = cp.asarray(vectors)

        clusterer = cuHDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric='euclidean',
            cluster_selection_method='eom',
        )
        labels = clusterer.fit_predict(vectors_gpu)
        return cp.asnumpy(labels)

    @staticmethod
    def build_cluster_output(
            face_data: List[Dict[str, Any]],
            labels: np.ndarray,
            save_noise: bool,
            episode_id: str,
            series_name: str,
            min_cluster_size: int,
            min_samples: int,
            model_name: str,
            total_frames: int,
    ) -> Dict[str, Any]:
        groups: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for face_info, label in zip(face_data, labels):
            groups[int(label)].append(face_info)

        clusters, noise_info = FaceClusterer.__build_cluster_entries(groups, save_noise)
        n_noise = len(groups.get(-1, []))
        frames_with_faces = len({fd['frame_path'] for fd in face_data})

        return {
            'episode_id': episode_id,
            'series_name': series_name,
            'processing_params': {
                'min_cluster_size': min_cluster_size,
                'min_samples': min_samples,
                'metric': 'euclidean',
                'algorithm': 'hdbscan',
                'cluster_selection_method': 'eom',
                'model': model_name,
            },
            'statistics': {
                'total_faces_detected': len(face_data),
                'total_clusters': len(clusters),
                'noise_faces': n_noise,
                'frames_processed': total_frames,
                'frames_with_faces': frames_with_faces,
            },
            'clusters': clusters,
            'noise': noise_info if save_noise else {},
        }

    @staticmethod
    def cleanup_gpu_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    @staticmethod
    def __build_cluster_entries(
            groups: Dict[int, List[Dict[str, Any]]],
            save_noise: bool,
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        clusters: Dict[str, Dict[str, Any]] = {}
        noise_info: Dict[str, Any] = {}

        for cluster_id, faces in sorted(groups.items()):
            frames_seen = sorted({fd['frame_path'].name for fd in faces})
            entry: Dict[str, Any] = {
                'face_count': len(faces),
                'frame_count': len(frames_seen),
                'frames': frames_seen,
                'character_name': None,
            }
            if cluster_id == -1:
                if save_noise:
                    noise_info = entry
            else:
                clusters[f'cluster_{cluster_id}'] = entry

        return clusters, noise_info
