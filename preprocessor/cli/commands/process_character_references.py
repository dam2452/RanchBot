from pathlib import Path
import sys

import click

from preprocessor.characters.reference_processor import CharacterReferenceProcessor
from preprocessor.cli.utils import create_state_manager
from preprocessor.config.config import settings


@click.command(context_settings={"show_default": True})
@click.option(
    "--characters-dir",
    type=click.Path(exists=True, path_type=Path),
    default=str(settings.character.output_dir),
    help="Directory with character reference images",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=str(settings.character.processed_references_dir),
    help="Output directory for processed references",
)
@click.option(
    "--similarity-threshold",
    type=float,
    default=settings.character.reference_matching_threshold,
    help="Threshold for face similarity when matching between reference images",
)
@click.option(
    "--interactive/--no-interactive",
    default=True,
    help="Enable interactive mode for ambiguous cases",
)
@click.option("--name", required=True, help="Series name")
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
def process_character_references(
    characters_dir: Path,
    output_dir: Path,
    similarity_threshold: float,
    interactive: bool,
    name: str,
    no_state: bool,
):
    """Process character reference images to identify and extract common faces."""
    state_manager = create_state_manager(name, no_state)

    processor = CharacterReferenceProcessor(
        {
            "characters_dir": characters_dir,
            "output_dir": output_dir,
            "similarity_threshold": similarity_threshold,
            "interactive": interactive,
            "series_name": name,
            "state_manager": state_manager,
        },
    )

    exit_code = processor.work()
    sys.exit(exit_code)
