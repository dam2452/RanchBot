from pathlib import Path
import sys

import click

from preprocessor.cli.utils import create_state_manager
from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import (
    TranscodeConfig,
    settings,
)
from preprocessor.utils.resolution import Resolution
from preprocessor.video.transcoder import VideoTranscoder


@click.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--transcoded-videos",
    type=click.Path(path_type=Path),
    default=str(settings.transcode.output_dir),
    help=f"Output directory for transcoded videos (default: {settings.transcode.output_dir})",
)
@click.option(
    "--resolution",
    type=click.Choice(["360p", "480p", "720p", "1080p", "1440p", "2160p"]),
    default="1080p",
    help="Target resolution for videos (default: 1080p)",
)
@click.option(
    "--codec",
    help="Video codec: h264_nvenc (GPU), libx264 (CPU)",
)
@click.option(
    "--preset",
    help="FFmpeg preset: slow, medium, fast",
)
@click.option(
    "--crf",
    type=int,
    help="Quality (CRF): 0=best 51=worst, 18-28 recommended",
)
@click.option(
    "--gop-size",
    type=float,
    help="Keyframe interval in seconds",
)
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    help="JSON file with episode metadata",
)
@click.option("--name", help="Series name for state management and resume support")
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
@click.option(
    "--max-workers",
    type=int,
    help="Number of parallel workers",
)
def transcode(  # pylint: disable=too-many-arguments
    videos: Path,
    transcoded_videos: Path,
    resolution: str,
    codec: str,
    preset: str,
    crf: int,
    gop_size: float,
    episodes_info_json: Path,
    name: str,
    no_state: bool,
    max_workers: int,
):
    """Transcode videos to target resolution with FFmpeg."""
    if transcoded_videos is None:  # pylint: disable=duplicate-code
        transcoded_videos = settings.transcode.output_dir
    if codec is None:
        codec = settings.transcode.codec
    if preset is None:
        preset = settings.transcode.preset
    if crf is None:
        crf = settings.transcode.crf
    if gop_size is None:
        gop_size = settings.transcode.gop_size
    if max_workers is None:
        max_workers = settings.transcode.max_workers

    state_manager = create_state_manager(name, no_state)

    config = TranscodeConfig(
        videos=videos,
        transcoded_videos=transcoded_videos,
        resolution=Resolution.from_str(resolution),
        codec=codec,
        preset=preset,
        crf=crf,
        gop_size=gop_size,
        episodes_info_json=episodes_info_json,
    )
    config_dict = config.to_dict()
    config_dict["state_manager"] = state_manager
    config_dict["series_name"] = name or "unknown"
    config_dict["max_workers"] = max_workers

    with ResourceScope():
        transcoder = VideoTranscoder(config_dict)
        exit_code = transcoder.work()

    if state_manager and exit_code == 0:
        state_manager.cleanup()

    sys.exit(exit_code)
