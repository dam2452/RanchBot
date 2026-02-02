from collections import defaultdict
import gc
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from cuml.cluster import HDBSCAN as cuHDBSCAN
import cupy as cp
import cv2
from insightface.app import FaceAnalysis
import numpy as np
import torch

from preprocessor.characters.utils import init_face_detection
from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.core.file_naming import FileNamingConventions
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.utils.file_utils import atomic_write_json
from preprocessor.utils.metadata_utils import create_processing_metadata
from preprocessor.video.frame_processor import FrameSubProcessor


class FaceClusteringSubProcessor(FrameSubProcessor):
    def __init__(
        self,
        min_cluster_size: int,
        min_samples: int,
        save_noise: bool,
        save_full_frames: bool,
    ):
        super().__init__("Face Clustering")
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.save_noise = save_noise
        self.save_full_frames = save_full_frames
        self.face_app: Optional[FaceAnalysis] = None
        self.logger = ErrorHandlingLogger("FaceClusteringSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        if self.face_app is None:
            console.print("[cyan]Initializing face detection for clustering...[/cyan]")
            self.face_app = init_face_detection()
            console.print("[green]✓ Face detection initialized[/green]")

    def cleanup(self) -> None:
        self.face_app = None
        self.__cleanup_memory()

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def needs_ramdisk(self) -> bool:
        return False

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.face_clusters)
        series_name = item.metadata["series_name"]
        file_naming = FileNamingConventions(series_name)
        metadata_filename = file_naming.build_filename(
            episode_info,
            extension="json",
            suffix="_face_clusters",
        )
        metadata_output = episode_dir / metadata_filename
        return [OutputSpec(path=metadata_output, required=True)]

    def should_run(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> bool:
        expected = self.get_expected_outputs(item)
        return any(str(exp.path) in str(miss.path) for exp in expected for miss in missing_outputs)

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:
        self.initialize()

        episode_info = item.metadata["episode_info"]

        frame_files = sorted([
            f for f in ramdisk_frames_dir.glob("*.jpg")
            if f.is_file() and "frame_" in f.name
        ])

        if not frame_files:
            console.print(f"[yellow]No frames found in {ramdisk_frames_dir}[/yellow]")
            return

        console.print(f"[cyan]Extracting faces and vectors from {len(frame_files)} frames[/cyan]")

        face_data = self.__extract_faces_with_vectors(frame_files)

        if len(face_data) == 0:
            console.print("[yellow]No faces detected, skipping clustering[/yellow]")
            return

        console.print(f"[cyan]Clustering {len(face_data)} faces[/cyan]")
        labels = self.__cluster_faces(face_data)

        console.print("[cyan]Saving clusters[/cyan]")
        series_name = item.metadata["series_name"]
        self.__save_clusters(episode_info, face_data, labels, frame_files, series_name)

    def __extract_faces_with_vectors(self, frame_files: List[Path]) -> List[Dict[str, Any]]:
        face_data = []

        for idx, frame_path in enumerate(frame_files):
            if idx % 50 == 0:
                console.print(f"[cyan]Processing frame {idx}/{len(frame_files)}[/cyan]")

            img = cv2.imread(str(frame_path))
            if img is None:
                continue

            faces = self.face_app.get(img)

            for face_idx, face in enumerate(faces):
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox

                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(img.shape[1], x2)
                y2 = min(img.shape[0], y2)

                face_img = img[y1:y2, x1:x2]

                if face_img.size == 0:
                    continue

                face_data.append({
                    'vector': face.normed_embedding,
                    'frame_path': frame_path,
                    'bbox': bbox,
                    'face_img': face_img,
                    'face_idx': face_idx,
                })

        console.print(f"[green]✓ Found {len(face_data)} faces in {len(frame_files)} frames[/green]")
        return face_data

    def __cluster_faces(self, face_data: List[Dict[str, Any]]) -> np.ndarray:
        vectors = np.array([fd['vector'] for fd in face_data])

        console.print(f"[cyan]Clustering with GPU HDBSCAN (min_cluster_size={self.min_cluster_size}, min_samples={self.min_samples})[/cyan]")
        vectors_gpu = cp.asarray(vectors)

        clusterer = cuHDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric='euclidean',
            cluster_selection_method='eom',
        )
        labels = clusterer.fit_predict(vectors_gpu)
        labels = cp.asnumpy(labels)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)

        console.print(f"[green]✓ Found {n_clusters} clusters[/green]")
        console.print(f"[green]✓ {n_noise} faces marked as noise[/green]")

        return labels

    def __save_clusters(  # pylint: disable=too-many-locals
        self,
        episode_info,
        face_data: List[Dict[str, Any]],
        labels: np.ndarray,
        all_frame_files: List[Path],
        series_name: str,
    ) -> None:
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.face_clusters)
        episode_dir.mkdir(parents=True, exist_ok=True)

        clusters = defaultdict(list)
        for face_info, label in zip(face_data, labels):
            clusters[label].append(face_info)

        cluster_stats = []

        for cluster_id, faces in sorted(clusters.items()):
            if cluster_id == -1:
                if not self.save_noise:
                    continue
                cluster_dir = episode_dir / "noise"
            else:
                cluster_dir = episode_dir / f"cluster_{cluster_id}"

            faces_dir = cluster_dir / "faces"
            faces_dir.mkdir(parents=True, exist_ok=True)

            if self.save_full_frames:
                frames_dir = cluster_dir / "frames"
                frames_dir.mkdir(parents=True, exist_ok=True)

            saved_frames = set()
            cluster_frames = []

            for face_info in faces:
                frame_name = face_info['frame_path'].stem
                face_idx = face_info['face_idx']
                face_output_path = faces_dir / f"{frame_name}_face{face_idx}.jpg"

                if face_info['face_img'].size > 0:
                    cv2.imwrite(str(face_output_path), face_info['face_img'])

                if self.save_full_frames and frame_name not in saved_frames:
                    frame_output_path = frames_dir / f"{frame_name}.jpg"
                    img = cv2.imread(str(face_info['frame_path']))
                    if img is not None:
                        cv2.imwrite(str(frame_output_path), img)
                        saved_frames.add(frame_name)
                        cluster_frames.append(f"{frame_name}.jpg")

            cluster_label = "noise" if cluster_id == -1 else f"cluster_{cluster_id}"
            console.print(f"[green]✓ Saved {len(faces)} faces to {cluster_label}[/green]")

            cluster_stats.append({
                "cluster_id": cluster_label,
                "face_count": len(faces),
                "frame_count": len(saved_frames),
                "frames": sorted(cluster_frames),
                "character_name": None,
            })

        self.__save_metadata(episode_info, face_data, labels, cluster_stats, all_frame_files, series_name)

    def __save_metadata(
        self,
        episode_info,
        face_data: List[Dict[str, Any]],
        labels: np.ndarray,
        cluster_stats: List[Dict[str, Any]],
        all_frame_files: List[Path],
        series_name: str,
    ) -> None:
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.face_clusters)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)
        frames_with_faces = len(set(fd['frame_path'] for fd in face_data))

        metadata = create_processing_metadata(
            episode_info=episode_info,
            processing_params={
                "min_cluster_size": self.min_cluster_size,
                "min_samples": self.min_samples,
                "metric": "euclidean",
                "algorithm": "hdbscan",
                "model": settings.face_recognition.model_name,
            },
            statistics={
                "total_faces_detected": len(face_data),
                "total_clusters": n_clusters,
                "noise_faces": n_noise,
                "frames_processed": len(all_frame_files),
                "frames_with_faces": frames_with_faces,
            },
            results_key="clusters",
            results_data=cluster_stats,
        )
        file_naming = FileNamingConventions(series_name)
        metadata_filename = file_naming.build_filename(
            episode_info,
            extension="json",
            suffix="_face_clusters",
        )
        metadata_output = episode_dir / metadata_filename
        atomic_write_json(metadata_output, metadata, indent=2, ensure_ascii=False)

        console.print(f"[green]✓ Saved cluster metadata to: {metadata_output}[/green]")

    @staticmethod
    def __cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
