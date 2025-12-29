from __future__ import annotations

import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from insightface.app import FaceAnalysis
import numpy as np

# pylint: disable=duplicate-code

from preprocessor.characters.face_detection_utils import load_character_references
from preprocessor.characters.utils import init_face_detection
from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.utils.console import console
from preprocessor.utils.detection_io import (
    process_frames_for_detection,
    save_character_detections,
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
        self.character_vectors = load_character_references(self.characters_dir, self.face_app)

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

        results = process_frames_for_detection(
            frame_files,
            self.face_app,
            self.character_vectors,
            self.threshold,
        )
        save_character_detections(episode_info, results)
