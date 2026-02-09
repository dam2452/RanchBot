from pathlib import Path
import sys

import click

from preprocessor.cli.utils import create_state_manager
from preprocessor.config.config import settings
from preprocessor.processors.frame_exporter import FrameExporter
from preprocessor.utils.resolution import Resolution


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
    default=None,
    help="Directory with scene timestamps",
)
@click.option(
    "--output-frames",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for exported frames",
)
@click.option(
    "--resolution",
    type=click.Choice(Resolution.get_all_choices()),
    default="1080p",
    help="Target resolution for exported frames",
)
@click.option("--name", required=True, help="Series name")
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
def export_frames(
    transcoded_videos: Path,
    episodes_info_json: Path,
    scene_timestamps_dir: Path,
    output_frames: Path,
    resolution: str,
    name: str,
    no_state: bool,
):
    """Export keyframes at target resolution based on configured keyframe strategy."""
    if scene_timestamps_dir is None:
        scene_timestamps_dir = settings.scene_detection.get_output_dir(name)
    if output_frames is None:
        output_frames = settings.frame_export.get_output_dir(name)

    state_manager = create_state_manager(name, no_state)

    res = Resolution.from_str(resolution)

    exporter = FrameExporter(
        {
            "transcoded_videos": transcoded_videos,
            "scene_timestamps_dir": scene_timestamps_dir,
            "output_frames": output_frames,
            "resolution": res,
            "series_name": name,
            "episodes_info_json": episodes_info_json,
            "state_manager": state_manager,
        },
    )

    exit_code = exporter.work()
    sys.exit(exit_code)
