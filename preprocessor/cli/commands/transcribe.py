from pathlib import Path
import sys

import click

# pylint: disable=duplicate-code

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import (
    TranscriptionConfig,
    settings,
)
from preprocessor.transcription.generator import TranscriptionGenerator


@click.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="JSON file with episode metadata (required)",
)
@click.option(
    "--transcription-jsons",
    type=click.Path(path_type=Path),
    default=str(settings.transcription.output_dir),
    help=f"Output directory for transcription JSONs (default: {settings.transcription.output_dir})",
)
@click.option(
    "--model",
    default=settings.transcription.model,
    help=f"Whisper model: tiny, base, small, medium, large, large-v3-turbo (default: {settings.transcription.model})",
)
@click.option(
    "--language",
    default=settings.transcription.language,
    help=f"Language for transcription (default: {settings.transcription.language})",
)
@click.option(
    "--device",
    default=settings.transcription.device,
    help=f"Device: cuda (GPU) or cpu (default: {settings.transcription.device})",
)
@click.option(
    "--extra-json-keys",
    multiple=True,
    help="Additional JSON keys to remove from output (can specify multiple times)",
)
@click.option(
    "--name",
    required=True,
    help="Series name for output files (required)",
)
@click.option(
    "--max-workers",
    type=int,
    default=1,
    help="Number of parallel workers for audio normalization (default: 1)",
)
def transcribe(
    videos: Path,
    episodes_info_json: Path,
    transcription_jsons: Path,
    model: str,
    language: str,
    device: str,
    extra_json_keys: tuple,
    name: str,
    max_workers: int,
):
    """Generate transcriptions using Whisper."""
    config = TranscriptionConfig(
        videos=videos,
        episodes_info_json=episodes_info_json,
        transcription_jsons=transcription_jsons,
        model=model,
        language=language,
        device=device,
        extra_json_keys_to_remove=list(extra_json_keys),
        name=name,
    )

    config_dict = config.to_dict()
    config_dict["max_workers"] = max_workers

    with ResourceScope():
        generator = TranscriptionGenerator(config_dict)
        exit_code = generator.work()

    sys.exit(exit_code)
