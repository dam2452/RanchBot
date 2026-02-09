from pathlib import Path
import sys

import click

from preprocessor.cli.utils import create_state_manager
from preprocessor.config.config import settings
from preprocessor.processors.image_hash_processor import ImageHashProcessor


@click.command(context_settings={"show_default": True})
@click.option(
    "--frames-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Directory with exported frames",
)
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="JSON file with episode metadata",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for image hashes",
)
@click.option(
    "--batch-size",
    type=int,
    default=settings.embedding.batch_size,
    help="Batch size for processing",
)
@click.option("--name", required=True, help="Series name")
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
def image_hashing(
    frames_dir: Path,
    episodes_info_json: Path,
    output_dir: Path,
    batch_size: int,
    name: str,
    no_state: bool,
):
    """Generate perceptual hashes for exported frames."""
    if frames_dir is None:
        frames_dir = settings.frame_export.get_output_dir(name)
    if output_dir is None:
        output_dir = settings.image_hash.get_output_dir(name)

    state_manager = create_state_manager(name, no_state)

    hasher = ImageHashProcessor(
        {
            "frames_dir": frames_dir,
            "output_dir": output_dir,
            "batch_size": batch_size,
            "device": "cuda",
            "series_name": name,
            "episodes_info_json": episodes_info_json,
            "state_manager": state_manager,
        },
    )

    exit_code = hasher.work()
    hasher.cleanup()
    sys.exit(exit_code)
