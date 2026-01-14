import sys
from pathlib import Path

import click

from preprocessor.validation.validator import Validator


@click.command(context_settings={"show_default": True})
@click.option(
    "--season",
    type=str,
    required=True,
    help="Season to validate (e.g., S10)",
)
@click.option(
    "--output-report",
    type=click.Path(path_type=Path),
    default="validation_report.json",
    help="Output JSON report path",
)
@click.option(
    "--anomaly-threshold",
    type=float,
    default=20.0,
    help="Threshold for anomaly detection (%)",
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
    help="JSON file with episode metadata (optional, for episode titles)",
)
def validate(
    season: str,
    output_report: Path,
    anomaly_threshold: float,
    series_name: str,
    episodes_info_json: Path,
):
    """Validate preprocessor output for a season."""
    validator = Validator(
        season=season,
        series_name=series_name,
        anomaly_threshold=anomaly_threshold,
        episodes_info_json=episodes_info_json,
    )

    exit_code = validator.validate(output_report)
    sys.exit(exit_code)
