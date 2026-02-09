from pathlib import Path
import sys

import click

from preprocessor.processors.text_analyzer import TextAnalyzer


@click.command(context_settings={"show_default": True})
@click.option(
    "--season",
    type=str,
    help="Season to analyze (e.g., S10). If not provided, analyzes all seasons",
)
@click.option(
    "--episode",
    type=str,
    help="Episode to analyze (e.g., E01). Requires --season. If not provided, analyzes all episodes in season",
)
@click.option(
    "--language",
    type=str,
    default="pl",
    help="Language code for analysis (pl or en)",
)
@click.option(
    "--series-name",
    type=str,
    default="ranczo",
    help="Series name for file naming",
)
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    help="JSON file with episode metadata (optional)",
)
def analyze_text(
    season: str,
    episode: str,
    language: str,
    series_name: str,
    episodes_info_json: Path,
):
    """Analyze transcription texts and generate linguistic statistics."""
    if episode and not season:
        click.echo("Error: --episode requires --season to be specified")
        sys.exit(1)

    analyzer = TextAnalyzer(
        {
            "series_name": series_name,
            "episodes_info_json": episodes_info_json,
            "language": language,
            "state_manager": None,
        },
    )

    exit_code = analyzer.work()
    sys.exit(exit_code)
