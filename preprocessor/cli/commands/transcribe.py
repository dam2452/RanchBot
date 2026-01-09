from pathlib import Path
import sys

import click

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import (
    TranscriptionConfig,
    settings,
)
from preprocessor.transcription.generator import TranscriptionGenerator

# pylint: disable=duplicate-code



@click.command(context_settings={"show_default": True})
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="JSON file with episode metadata",
)
@click.option(
    "--transcription-jsons",
    type=click.Path(path_type=Path),
    default=str(settings.transcription.output_dir),
    help="Output directory for transcription JSONs",
)
@click.option(
    "--model",
    default=settings.transcription.model,
    help="Whisper model: tiny, base, small, medium, large, large-v3-turbo",
)
@click.option(
    "--language",
    default=settings.transcription.language,
    help="Language for transcription",
)
@click.option(
    "--extra-json-keys",
    multiple=True,
    help="Additional JSON keys to remove from output (can specify multiple times)",
)
@click.option(
    "--name",
    required=True,
    help="Series name for output files",
)
def transcribe(
    videos: Path,
    episodes_info_json: Path,
    transcription_jsons: Path,
    model: str,
    language: str,
    extra_json_keys: tuple,
    name: str,
):
    """Generate transcriptions using Whisper."""
    config = TranscriptionConfig(
        videos=videos,
        episodes_info_json=episodes_info_json,
        transcription_jsons=transcription_jsons,
        model=model,
        language=language,
        device="cuda",
        extra_json_keys_to_remove=list(extra_json_keys),
        name=name,
    )

    config_dict = config.to_dict()

    with ResourceScope():
        generator = TranscriptionGenerator(config_dict)
        exit_code = generator.work()

    sys.exit(exit_code)
