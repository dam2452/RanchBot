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


@click.command(context_settings={"show_default": True})
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--transcoded-videos",
    type=click.Path(path_type=Path),
    default=str(settings.transcode.output_dir),
    help="Output directory for transcoded videos",
)
@click.option(
    "--resolution",
    type=click.Choice(Resolution.get_all_choices()),
    default="720p",
    help="Target resolution for videos",
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
def transcode(
    videos: Path,
    transcoded_videos: Path,
    resolution: str,
    codec: str,
    preset: str,
    gop_size: float,
    episodes_info_json: Path,
    name: str,
    no_state: bool,
):
    """Transcode videos to target resolution with FFmpeg."""
    if transcoded_videos is None:  # pylint: disable=duplicate-code
        transcoded_videos = settings.transcode.output_dir
    if codec is None:
        codec = settings.transcode.codec
    if preset is None:
        preset = settings.transcode.preset
    if gop_size is None:
        gop_size = settings.transcode.gop_size

    state_manager = create_state_manager(name, no_state)

    video_bitrate_mbps = settings.transcode.calculate_video_bitrate_mbps()
    minrate_mbps = settings.transcode.calculate_minrate_mbps()
    maxrate_mbps = settings.transcode.calculate_maxrate_mbps()
    bufsize_mbps = settings.transcode.calculate_bufsize_mbps()

    config = TranscodeConfig(
        videos=videos,
        transcoded_videos=transcoded_videos,
        resolution=Resolution.from_str(resolution),
        codec=codec,
        preset=preset,
        gop_size=gop_size,
        episodes_info_json=episodes_info_json,
        video_bitrate_mbps=video_bitrate_mbps,
        minrate_mbps=minrate_mbps,
        maxrate_mbps=maxrate_mbps,
        bufsize_mbps=bufsize_mbps,
        audio_bitrate_kbps=settings.transcode.audio_bitrate_kbps,
    )
    config_dict = config.to_dict()
    config_dict["state_manager"] = state_manager
    config_dict["series_name"] = name or "unknown"

    with ResourceScope():
        transcoder = VideoTranscoder(config_dict)
        exit_code = transcoder.work()

    if state_manager and exit_code == 0:
        state_manager.cleanup()

    sys.exit(exit_code)
