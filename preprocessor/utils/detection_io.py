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
    detections_output_dir = Path(settings.character.detections_dir)
    season = episode_info.season
    episode = episode_info.relative_episode
    episode_dir = detections_output_dir / f"S{season:02d}" / f"E{episode:02d}"
    episode_dir.mkdir(parents=True, exist_ok=True)

    detections_data = {
        "episode_info": create_minimal_episode_info(episode_info),
        "video_metadata": {
            "fps": fps,
        },
        "detections": results,
    }

    series_name = episode_info.series_name if hasattr(episode_info, 'series_name') else 'unknown'
    file_naming = FileNamingConventions(series_name)
    detections_filename = file_naming.build_filename(
        episode_info,
        extension="json",
        suffix="_character_detections",
    )
    detections_output = episode_dir / detections_filename
    atomic_write_json(detections_output, detections_data, indent=2, ensure_ascii=False)

    frames_with_chars = sum(1 for r in results if r["characters"])
    console.print(f"[green]✓ S{season:02d}E{episode:02d}: {len(results)} frames, {frames_with_chars} with characters[/green]")


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
