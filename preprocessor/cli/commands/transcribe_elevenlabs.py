from pathlib import Path
import sys

import click

from preprocessor.cli.utils import create_state_manager
from preprocessor.config.config import settings
from preprocessor.transcription.elevenlabs import ElevenLabsTranscriber
from preprocessor.utils.console import console


@click.command(name="transcribe-elevenlabs")
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=str(settings.transcription.output_dir),
    help=f"Output directory for transcriptions (default: {settings.transcription.output_dir})",
)
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    help="JSON file with episode metadata (optional)",
)
@click.option("--name", required=True, help="Series name (required)")
@click.option(
    "--api-key",
    envvar="ELEVEN_API_KEY",
    help="ElevenLabs API key (or set ELEVEN_API_KEY env var)",
)
@click.option(
    "--model-id",
    default="scribe_v1",
    help="ElevenLabs model ID (default: scribe_v1)",
)
@click.option(
    "--language-code",
    default="pol",
    help="Language code: pol, eng, etc (default: pol)",
)
@click.option(
    "--diarize/--no-diarize",
    default=True,
    help="Enable speaker diarization (default: enabled)",
)
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
def transcribe_elevenlabs(
    videos: Path,
    output_dir: Path,
    episodes_info_json: Path,
    name: str,
    api_key: str,
    model_id: str,
    language_code: str,
    diarize: bool,
    no_state: bool,
):
    """Transcribe videos using ElevenLabs API."""
    state_manager = create_state_manager(name, no_state)

    transcriber = ElevenLabsTranscriber(
        {
            "videos": videos,
            "output_dir": output_dir,
            "episodes_info_json": episodes_info_json,
            "series_name": name,
            "api_key": api_key,
            "model_id": model_id,
            "language_code": language_code,
            "diarize": diarize,
            "state_manager": state_manager,
        },
    )

    exit_code = transcriber.work()

    if state_manager and exit_code == 0:
        console.print("[green]Transcription completed successfully![/green]")
        state_manager.cleanup()

    sys.exit(exit_code)
