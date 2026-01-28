from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.characters.face_detection_utils import detect_characters_in_frame
from preprocessor.config.config import settings
from preprocessor.core.file_naming import FileNamingConventions
from preprocessor.core.output_path_builder import OutputPathBuilder
from preprocessor.utils.console import console
from preprocessor.utils.file_utils import atomic_write_json
from preprocessor.utils.metadata_utils import create_minimal_episode_info


def parse_frame_number(frame_filename: str) -> Optional[int]:
    match = re.search(r'frame_(\d+)', frame_filename)
    if match:
        return int(match.group(1))
    return None


def save_character_detections(
    episode_info,
    results: List[Dict[str, Any]],
    fps: float = 25.0,
) -> None:
    detections_data = {
        "episode_info": create_minimal_episode_info(episode_info),
        "video_metadata": {
            "fps": fps,
        },
        "detections": results,
    }

    file_naming = FileNamingConventions(episode_info.series_name)
    detections_filename = file_naming.build_filename(
        episode_info,
        extension="json",
        suffix="character_detections",
    )
    detections_output = OutputPathBuilder.build_output_path(
        episode_info,
        settings.output_subdirs.character_detections,
        detections_filename,
    )
    atomic_write_json(detections_output, detections_data, indent=2, ensure_ascii=False)

    frames_with_chars = sum(1 for r in results if r["characters"])
    console.print(
        f"[green]✓ {episode_info.episode_code()}: {len(results)} frames, "
        f"{frames_with_chars} with characters[/green]",
    )


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

        frame_number = parse_frame_number(frame_path.name)
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
