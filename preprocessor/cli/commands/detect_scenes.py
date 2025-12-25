from pathlib import Path
import sys

import click

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import settings
from preprocessor.video.scene_detector import SceneDetector


@click.command(name="detect-scenes")
@click.argument("videos", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=str(settings.scene_detection.output_dir),
    help=f"Output directory for scene JSON files (default: {settings.scene_detection.output_dir})",
)
@click.option(
    "--threshold",
    type=float,
    default=settings.scene_detection.threshold,
    help=f"Scene detection threshold 0.0-1.0 (default: {settings.scene_detection.threshold})",
)
@click.option(
    "--min-scene-len",
    type=int,
    default=settings.scene_detection.min_scene_len,
    help=f"Minimum scene length in frames (default: {settings.scene_detection.min_scene_len})",
)
def detect_scenes(videos: Path, output_dir: Path, threshold: float, min_scene_len: int):
    """Detect scene changes in videos using TransNetV2."""
    with ResourceScope():
        detector = SceneDetector(
            {
                "videos": videos,
                "output_dir": output_dir,
                "threshold": threshold,
                "min_scene_len": min_scene_len,
            },
        )
        exit_code = detector.work()
        detector.cleanup()

    sys.exit(exit_code)
