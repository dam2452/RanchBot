from pathlib import Path
import sys

import click

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import settings
from preprocessor.transcription.processors.sound_separator import SoundEventSeparator


@click.command(context_settings={"show_default": True})
@click.option(
    "--transcription-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Directory with transcription JSON files",
)
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="JSON file with episode metadata",
)
@click.option(
    "--series-name",
    required=True,
    help="Series name",
)
def separate_sounds(
    transcription_dir: Path,
    episodes_info_json: Path,
    series_name: str,
):
    """Separate sound events from dialogues in transcription files."""
    if transcription_dir is None:
        transcription_dir = settings.transcription.get_output_dir(series_name)

    args = {
        "transcription_dir": transcription_dir,
        "episodes_info_json": episodes_info_json,
        "series_name": series_name,
    }

    with ResourceScope():
        separator = SoundEventSeparator(args)
        exit_code = separator.work()

    sys.exit(exit_code)
