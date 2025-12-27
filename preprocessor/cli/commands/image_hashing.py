from pathlib import Path
import sys

import click

from preprocessor.cli.utils import create_state_manager
from preprocessor.config.config import settings
from preprocessor.hashing.image_hash_processor import ImageHashProcessor


@click.command()
@click.option(
    "--frames-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=str(settings.frame_export.output_dir),
    help=f"Directory with exported frames (default: {settings.frame_export.output_dir})",
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
    default=str(settings.image_hash.output_dir),
    help=f"Output directory for image hashes (default: {settings.image_hash.output_dir})",
)
@click.option(
    "--batch-size",
    type=int,
    default=settings.embedding.batch_size,
    help=f"Batch size for processing (default: {settings.embedding.batch_size})",
)
@click.option("--name", required=True, help="Series name (required)")
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
