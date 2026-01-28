from pathlib import Path
import sys

import click

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import settings
from preprocessor.transcription.processors.unicode_fixer import TranscriptionUnicodeFixer


@click.command(context_settings={"show_default": True})
@click.option(
    "--transcription-jsons",
    type=click.Path(exists=True, path_type=Path),
    default=str(settings.transcription.output_dir),
    help="Directory with transcription JSON files",
)
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="JSON file with episode metadata",
)
@click.option(
    "--name",
    required=True,
    help="Series name",
)
def fix_unicode(
    transcription_jsons: Path,
    episodes_info_json: Path,
    name: str,
):
    """Fix unicode escape sequences in transcription files."""
    args = {
        "transcription_jsons": transcription_jsons,
        "episodes_info_json": episodes_info_json,
        "name": name,
    }

    with ResourceScope():
        fixer = TranscriptionUnicodeFixer(args)
        exit_code = fixer.work()

    sys.exit(exit_code)
