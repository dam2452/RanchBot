from pathlib import Path
import sys

import click

from preprocessor.cli.utils import create_state_manager
from preprocessor.config.config import settings
from preprocessor.processors.transcription_importer import TranscriptionImporter
from preprocessor.utils.console import console


@click.command(name="import-transcriptions", context_settings={"show_default": True})
@click.option(
    "--source-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory with source transcriptions (11labs format)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for converted transcriptions",
)
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    help="JSON file with episode metadata",
)
@click.option("--name", required=True, help="Series name")
@click.option(
    "--format-type",
    type=click.Choice(["11labs_segmented", "11labs"]),
    default="11labs_segmented",
    help="Source format: 11labs_segmented or 11labs",
)
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
def import_transcriptions(
    source_dir: Path,
    output_dir: Path,
    episodes_info_json: Path,
    name: str,
    format_type: str,
    no_state: bool,
):
    """Import and convert transcriptions from external sources."""
    if output_dir is None:
        output_dir = settings.transcription.get_output_dir(name)

    state_manager = create_state_manager(name, no_state)

    importer = TranscriptionImporter(
        {
            "source_dir": source_dir,
            "output_dir": output_dir,
            "episodes_info_json": episodes_info_json,
            "series_name": name,
            "format_type": format_type,
            "state_manager": state_manager,
        },
    )

    exit_code = importer.work()

    if state_manager and exit_code == 0:
        console.print("[green]Import completed successfully![/green]")
        state_manager.cleanup()

    sys.exit(exit_code)
