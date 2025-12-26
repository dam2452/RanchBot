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

from preprocessor.config.config import settings
from preprocessor.core.base_processor import BaseProcessor
from preprocessor.utils.console import (
    console,
    create_progress,
)


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
        self.output_json: Path = self._args["output_json"]
        self.threshold: float = settings.face_recognition.threshold
        self.use_gpu: bool = settings.face_recognition.use_gpu

        self.face_app: FaceAnalysis = None
        self.character_vectors: Dict[str, np.ndarray] = {}

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "frames_dir" not in args:
            raise ValueError("frames_dir is required")
        if "output_json" not in args:
            raise ValueError("output_json is required")

    def _execute(self) -> None:
        if not self.frames_dir.exists():
            console.print(f"[red]Frames directory not found: {self.frames_dir}[/red]")
            return

        if not self.characters_dir.exists():
            console.print(f"[red]Characters directory not found: {self.characters_dir}[/red]")
            return

        self._init_face_detection()
        self._load_character_references()

        if not self.character_vectors:
            console.print("[yellow]No character references loaded[/yellow]")
            return

        console.print("[blue]Detecting characters in frames...[/blue]")
        results = self._detect_in_all_frames()

        self.output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        total_frames = len(results)
        frames_with_chars = sum(1 for r in results if r["characters"])
        console.print(f"[green]✓ Processed {total_frames} frames[/green]")
        console.print(f"[green]✓ Found characters in {frames_with_chars} frames[/green]")
        console.print(f"[green]✓ Results saved to: {self.output_json}[/green]")

    def _init_face_detection(self):
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.use_gpu else ['CPUExecutionProvider']
        self.face_app = FaceAnalysis(name=settings.face_recognition.model_name, providers=providers)
        ctx_id = 0 if self.use_gpu else -1
        self.face_app.prepare(ctx_id=ctx_id, det_size=settings.face_recognition.detection_size)
        console.print(f"[green]✓ Face detection initialized ({settings.face_recognition.model_name})[/green]")

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

    def _detect_in_all_frames(self) -> List[Dict[str, Any]]:
        frame_files = sorted([
            f for f in self.frames_dir.rglob("*.jpg")
            if f.is_file()
        ])

        results = []

        with create_progress() as progress:
            task = progress.add_task("Detecting characters", total=len(frame_files))

            for frame_path in frame_files:
                try:
                    detected_chars = self._detect_in_frame(frame_path)
                    relative_path = frame_path.relative_to(self.frames_dir)

                    results.append({
                        "frame": str(relative_path),
                        "characters": detected_chars,
                    })

                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.error(f"Error processing {frame_path}: {e}")

                progress.advance(task)

        return results

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
