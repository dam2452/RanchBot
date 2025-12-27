from __future__ import annotations

import json
import logging
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

from preprocessor.characters.utils import init_face_detection
from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.utils.console import console


class CharacterDetector(BaseProcessor):
    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=9,
            loglevel=logging.DEBUG,
        )

        self.frames_dir: Path = self._args["frames_dir"]
        self.characters_dir: Path = self._args.get("characters_dir", settings.character.output_dir)
        self.output_dir: Path = self._args.get("output_dir", settings.character.detections_dir)
        self.threshold: float = settings.face_recognition.threshold
        self.use_gpu: bool = settings.face_recognition.use_gpu

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

        self.face_app: FaceAnalysis = None
        self.character_vectors: Dict[str, np.ndarray] = {}

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "frames_dir" not in args:
            raise ValueError("frames_dir is required")

    # pylint: disable=duplicate-code
    def _get_processing_items(self) -> List[ProcessingItem]:
        return self._get_episode_processing_items_from_metadata(
            "**/frame_metadata.json",
            self.frames_dir,
            self.episode_manager,
        )

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = self._build_episode_output_dir(episode_info, self.output_dir)
        detections_output = episode_dir / "detections.json"
        return [OutputSpec(path=detections_output, required=True)]
    # pylint: enable=duplicate-code

    def _execute_processing(self, items: List[ProcessingItem]) -> None:
        if not self.characters_dir.exists():
            console.print(f"[red]Characters directory not found: {self.characters_dir}[/red]")
            return

        self.face_app = init_face_detection(self.use_gpu)
        self._load_character_references()

        if not self.character_vectors:
            console.print("[yellow]No character references loaded[/yellow]")
            return

        super()._execute_processing(items)
        console.print("[green]Character detection completed[/green]")

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        metadata_file = item.input_path
        episode_info = item.metadata["episode_info"]
        frames_dir = metadata_file.parent

        frame_files = sorted([
            f for f in frames_dir.glob("*.jpg")
            if f.is_file() and f.name.startswith("frame_")
        ])

        results = []
        for frame_path in frame_files:
            detected_chars = self._detect_in_frame(frame_path)
            results.append({
                "frame": frame_path.name,
                "characters": detected_chars,
            })

        self._save_detections(episode_info, results)

    def _load_character_references(self):
        console.print("[blue]Loading character references...[/blue]")

        for char_dir in self.characters_dir.iterdir():
            if not char_dir.is_dir():
                continue

            char_name = char_dir.name.replace("_", " ").title()
            images = list(char_dir.glob("*.jpg"))

            if not images:
                continue

            embeddings = []
            for img_path in images:
                emb = self._get_embedding(str(img_path))
                if emb is not None:
                    embeddings.append(emb)

            if embeddings:
                mean_emb = np.mean(embeddings, axis=0)
                centroid = mean_emb / norm(mean_emb)
                self.character_vectors[char_name] = centroid
                console.print(f"[green]  ✓ {char_name}: {len(embeddings)} reference images[/green]")

        console.print(f"[green]✓ Loaded {len(self.character_vectors)} characters[/green]")

    def _get_embedding(self, img_path: str) -> Optional[np.ndarray]:
        img = cv2.imread(img_path)
        if img is None:
            return None

        faces = self.face_app.get(img)
        if not faces:
            return None

        faces.sort(key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
        return faces[0].normed_embedding

    def _save_detections(self, episode_info, results: List[Dict[str, Any]]) -> None:
        season = episode_info.season
        episode = episode_info.relative_episode
        episode_dir = self.output_dir / f"S{season:02d}" / f"E{episode:02d}"
        episode_dir.mkdir(parents=True, exist_ok=True)

        minimal_episode_info = {
            "season": episode_info.season,
            "episode_number": episode_info.relative_episode,
        }

        detections_data = {
            "episode_info": minimal_episode_info,
            "detections": results,
        }

        detections_output = episode_dir / "detections.json"
        with open(detections_output, "w", encoding="utf-8") as f:
            json.dump(detections_data, f, indent=2, ensure_ascii=False)

        frames_with_chars = sum(1 for r in results if r["characters"])
        console.print(f"[green]✓ S{season:02d}E{episode:02d}: {len(results)} frames, {frames_with_chars} with characters[/green]")

    def _detect_in_frame(self, frame_path: Path) -> List[Dict[str, Any]]:
        img = cv2.imread(str(frame_path))
        if img is None:
            return []

        faces = self.face_app.get(img)
        if not faces:
            return []

        detected = []

        for face in faces:
            face_embedding = face.normed_embedding

            for char_name, char_vector in self.character_vectors.items():
                similarity = np.dot(face_embedding, char_vector)

                if similarity > self.threshold:
                    detected.append({
                        "name": char_name,
                        "confidence": float(similarity),
                    })

        detected.sort(key=lambda x: x["confidence"], reverse=True)
        return detected
