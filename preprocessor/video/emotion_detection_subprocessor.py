import json
import logging
from pathlib import Path
from typing import (
    List,
    Optional,
)

import cv2
import onnxruntime as ort

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.utils.console import console
from preprocessor.utils.emotion_utils import (
    crop_face_from_frame,
    detect_emotions_batch,
    init_emotion_model,
)
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.utils.file_utils import atomic_write_json
from preprocessor.video.frame_processor import FrameSubProcessor


class EmotionDetectionSubProcessor(FrameSubProcessor):
    def __init__(self, model_path: Optional[Path] = None):
        super().__init__("Emotion Detection")
        self.model_path = model_path
        self.session: Optional[ort.InferenceSession] = None
        self.logger = ErrorHandlingLogger("EmotionDetectionSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        if self.session is None:
            self.session = init_emotion_model(self.model_path)

    def cleanup(self) -> None:
        self.session = None

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        return []

    def should_run(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> bool:
        episode_info = item.metadata["episode_info"]
        detections_file = (
            EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.character_detections) /
            "detections.json"
        )

        if not detections_file.exists():
            console.print(
                f"[yellow]No character detections found for emotion analysis: {detections_file}[/yellow]",
            )
            return False

        with open(detections_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for detection in data.get("detections", []):
            for char in detection.get("characters", []):
                if "emotion" in char:
                    return False

        return True

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:
        self.initialize()

        episode_info = item.metadata["episode_info"]

        detections_file = (
            EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.character_detections) /
            "detections.json"
        )

        if not detections_file.exists():
            console.print(f"[yellow]No detections file: {detections_file}[/yellow]")
            return

        with open(detections_file, "r", encoding="utf-8") as f:
            detections_data = json.load(f)

        detections = detections_data.get("detections", [])

        total_characters = sum(len(d.get("characters", [])) for d in detections)
        console.print(f"[cyan]Collecting {total_characters} faces for batch emotion analysis[/cyan]")

        face_crops = []
        face_metadata = []

        for detection_idx, detection in enumerate(detections):
            frame_file = detection.get("frame_file")
            if not frame_file:
                continue

            frame_path = ramdisk_frames_dir / frame_file

            if not frame_path.exists():
                continue

            frame = cv2.imread(str(frame_path))
            if frame is None:
                continue

            characters = detection.get("characters", [])

            for char_idx, char in enumerate(characters):
                bbox = char.get("bbox")
                if not bbox:
                    continue

                face_crop = crop_face_from_frame(frame, bbox)
                if face_crop is None:
                    continue

                face_crops.append(face_crop)
                face_metadata.append({
                    "detection_idx": detection_idx,
                    "char_idx": char_idx,
                })

        if not face_crops:
            console.print("[yellow]No valid face crops found[/yellow]")
            return

        console.print(f"[cyan]Processing {len(face_crops)} faces with optimized ONNX inference[/cyan]")

        emotion_results = detect_emotions_batch(face_crops, self.session)

        processed = 0
        for result, metadata in zip(emotion_results, face_metadata):
            if result is None:
                continue

            dominant_emotion, confidence, emotion_scores = result
            detection_idx = metadata["detection_idx"]
            char_idx = metadata["char_idx"]

            char = detections[detection_idx]["characters"][char_idx]
            char["emotion"] = {
                "label": dominant_emotion,
                "confidence": confidence,
                "scores": emotion_scores,
            }
            processed += 1

        atomic_write_json(detections_file, detections_data, indent=2, ensure_ascii=False)

        console.print(
            f"[green]✓ Emotion analysis complete: {processed}/{total_characters} characters processed[/green]",
        )
