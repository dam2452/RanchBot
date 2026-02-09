import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from insightface.app import FaceAnalysis
import numpy as np

from preprocessor.characters.face_detection import (
    init_face_detection,
    load_character_references,
)
from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.path_manager import PathManager
from preprocessor.utils.console import console
from preprocessor.utils.detection_io import (
    process_frames_for_detection,
    save_character_detections,
)
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.video.frame_processor import FrameSubProcessor


class CharacterDetectionSubProcessor(FrameSubProcessor):
    def __init__(self, characters_dir: Path, use_gpu: bool, threshold: float):
        super().__init__("Character Detection")
        self.characters_dir = characters_dir
        self.use_gpu = use_gpu
        self.threshold = threshold
        self.face_app: Optional[FaceAnalysis] = None
        self.character_vectors: Dict[str, np.ndarray] = {}
        self.logger = ErrorHandlingLogger("CharacterDetectionSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        if self.face_app is None:
            console.print("[cyan]Initializing face detection...[/cyan]")
            self.face_app = init_face_detection()
            self.character_vectors = load_character_references(self.characters_dir, self.face_app)
            console.print("[green]✓ Face detection initialized[/green]")

    def cleanup(self) -> None:
        self.face_app = None
        self.character_vectors = {}

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.character_detections)
        series_name = item.metadata["series_name"]
        path_manager = PathManager(series_name)
        detections_filename = path_manager.build_filename(
            episode_info,
            extension="json",
            suffix="character_detections",
        )
        detections_output = episode_dir / detections_filename
        return [OutputSpec(path=detections_output, required=True)]

    def should_run(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> bool:
        if not self.characters_dir.exists():
            console.print(f"[yellow]Characters directory not found: {self.characters_dir}, skipping[/yellow]")
            return False

        expected = self.get_expected_outputs(item)
        return any(str(exp.path) in str(miss.path) for exp in expected for miss in missing_outputs)

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:
        self.initialize()

        if not self.character_vectors:
            console.print("[yellow]No character references loaded, skipping detection[/yellow]")
            return

        episode_info = item.metadata["episode_info"]

        frame_files = sorted([
            f for f in ramdisk_frames_dir.glob("*.jpg")
            if f.is_file() and "frame_" in f.name
        ])

        console.print(f"[cyan]Detecting characters in {len(frame_files)} frames[/cyan]")

        fps = 25.0

        results = process_frames_for_detection(
            frame_files,
            self.face_app,
            self.character_vectors,
            self.threshold,
            fps=fps,
        )
        save_character_detections(episode_info, results, fps=fps)
