from pathlib import Path
import sys

import click

from preprocessor.cli.utils import create_state_manager
from preprocessor.config.config import settings
from preprocessor.video.frame_exporter import FrameExporter


@click.command(context_settings={"show_default": True})
@click.argument("transcoded_videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="JSON file with episode metadata",
)
@click.option(
    "--scene-timestamps-dir",
    type=click.Path(exists=True, path_type=Path),
    default=str(settings.scene_detection.output_dir),
    help="Directory with scene timestamps",
)
@click.option(
    "--output-frames",
    type=click.Path(path_type=Path),
    default=str(settings.frame_export.output_dir),
    help="Output directory for exported frames",
)
@click.option(
    "--frame-height",
    type=int,
    default=1080,
    help="Height of exported frames in pixels",
)
@click.option("--name", required=True, help="Series name")
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
def export_frames(
    transcoded_videos: Path,
    episodes_info_json: Path,
    scene_timestamps_dir: Path,
    output_frames: Path,
    frame_height: int,
    name: str,
    no_state: bool,
):
    """Export keyframes at 1080p resolution based on configured keyframe strategy."""
    state_manager = create_state_manager(name, no_state)

    exporter = FrameExporter(
        {
            "transcoded_videos": transcoded_videos,
            "scene_timestamps_dir": scene_timestamps_dir,
            "output_frames": output_frames,
            "frame_height": frame_height,
            "series_name": name,
            "episodes_info_json": episodes_info_json,
            "state_manager": state_manager,
        },
    )

    exit_code = exporter.work()
    sys.exit(exit_code)
