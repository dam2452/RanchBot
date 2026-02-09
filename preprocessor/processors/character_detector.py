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

from preprocessor.characters.face_detection import (
    init_face_detection,
    load_character_references,
)
from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.core.path_manager import PathManager
from preprocessor.core.processor_registry import register_processor
from preprocessor.utils.console import console
from preprocessor.utils.detection_io import (
    process_frames_for_detection,
    save_character_detections,
)

# pylint: disable=duplicate-code


@register_processor("detect_characters")
class CharacterDetector(BaseProcessor):
    REQUIRES = ["frames"]
    PRODUCES = ["character_detections"]
    PRIORITY = 60
    DESCRIPTION = "Detect characters in frames"

    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=9,
            loglevel=logging.DEBUG,
        )

        self.frames_dir: Path = self._args["frames_dir"]
        self.characters_dir: Path = self._args.get("characters_dir", settings.character.get_output_dir(self.series_name))
        self.threshold: float = settings.character.frame_detection_threshold

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

        self.face_app: FaceAnalysis = None
        self.character_vectors: Dict[str, np.ndarray] = {}

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "frames_dir" not in args:
            raise ValueError("frames_dir is required")

    def get_output_subdir(self) -> str:
        return settings.output_subdirs.character_detections

    # pylint: disable=duplicate-code
    def _get_processing_items(self) -> List[ProcessingItem]:
        return self._get_episode_processing_items_from_metadata(
            "**/*_frame_metadata.json",
            self.frames_dir,
            self.episode_manager,
        )

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        path_manager = PathManager(self.series_name)
        detections_filename = path_manager.build_filename(
            episode_info,
            extension="json",
            suffix="character_detections",
        )
        detections_output = self._build_output_path(episode_info, detections_filename)
        return [OutputSpec(path=detections_output, required=True)]
    # pylint: enable=duplicate-code

    def _load_resources(self) -> bool:
        if not self.characters_dir.exists():
            console.print(f"[red]Characters directory not found: {self.characters_dir}[/red]")
            return False

        self.face_app = init_face_detection()
        self.character_vectors = load_character_references(self.characters_dir, self.face_app)

        if not self.character_vectors:
            console.print("[yellow]No character references loaded[/yellow]")
            return False

        return True

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        metadata_file = item.input_path
        episode_info = item.metadata["episode_info"]
        frames_dir = metadata_file.parent

        frame_files = sorted([
            f for f in frames_dir.glob("*.jpg")
            if f.is_file() and "frame_" in f.name
        ])

        fps = 25.0

        results = process_frames_for_detection(
            frame_files,
            self.face_app,
            self.character_vectors,
            self.threshold,
            fps=fps,
        )
        save_character_detections(episode_info, results, self.path_manager, fps=fps)
