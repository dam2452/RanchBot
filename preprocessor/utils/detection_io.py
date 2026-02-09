from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.characters.face_detection import detect_characters_in_frame
from preprocessor.config.config import settings
from preprocessor.core.path_manager import PathManager
from preprocessor.utils.console import console
from preprocessor.utils.file_utils import atomic_write_json
from preprocessor.utils.metadata_utils import create_minimal_episode_info


def _parse_frame_number(frame_filename: str) -> Optional[int]:
    match = re.search(r'frame_(\d+)', frame_filename)
    if match:
        return int(match.group(1))
    return None


def save_character_detections(
    episode_info,
    results: List[Dict[str, Any]],
    path_manager: Optional[PathManager] = None,
    fps: float = 25.0,
) -> Path:
    detections_data = {
        "episode_info": create_minimal_episode_info(episode_info),
        "video_metadata": {
            "fps": fps,
        },
        "detections": results,
    }

    series_name = episode_info.series_name or "unknown"
    path_manager = PathManager(series_name)

    detections_filename = path_manager.build_filename(
        episode_info,
        extension="json",
        suffix="character_detections",
    )

    if path_manager is None:
        path_manager = PathManager(series_name)

    detections_output = path_manager.build_path(
        episode_info,
        settings.output_subdirs.character_detections,
        detections_filename,
    )
    atomic_write_json(detections_output, detections_data, indent=2, ensure_ascii=False)

    return detections_output


def process_frames_for_detection(
    frame_files: List[Path],
    face_app,
    character_vectors: Dict[str, Any],
    threshold: float,
    fps: float = 25.0,
) -> List[Dict[str, Any]]:
    results = []
    for idx, frame_path in enumerate(frame_files):
        detected_chars = detect_characters_in_frame(
            frame_path,
            face_app,
            character_vectors,
            threshold,
        )

        frame_number = _parse_frame_number(frame_path.name)
        timestamp = frame_number / fps if frame_number is not None else None

        frame_result = {
            "frame_number": frame_number,
            "timestamp": timestamp,
            "frame_file": frame_path.name,
            "characters": detected_chars,
        }

        results.append(frame_result)

        if (idx + 1) % 100 == 0:
            console.print(f"  Processed {idx + 1}/{len(frame_files)} frames")

    return results
