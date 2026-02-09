from pathlib import Path
import sys

import click

from preprocessor.config.config import settings
from preprocessor.processors.scene_detector import SceneDetector
from preprocessor.utils.resource_scope import ResourceScope


@click.command(name="detect-scenes", context_settings={"show_default": True})
@click.argument("videos", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for scene JSON files",
)
@click.option(
    "--threshold",
    type=float,
    default=settings.scene_detection.threshold,
    help="Scene detection threshold 0.0-1.0",
)
@click.option(
    "--min-scene-len",
    type=int,
    default=settings.scene_detection.min_scene_len,
    help="Minimum scene length in frames",
)
@click.option("--name", required=True, help="Series name")
def detect_scenes(videos: Path, output_dir: Path, threshold: float, min_scene_len: int, name: str):
    """Detect scene changes in videos using TransNetV2."""
    if output_dir is None:
        output_dir = settings.scene_detection.get_output_dir(name)

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
