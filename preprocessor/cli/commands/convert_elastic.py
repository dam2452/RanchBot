from pathlib import Path
import sys

import click

from preprocessor.legacy.legacy_converter import LegacyConverter


@click.command(name="convert-elastic")
@click.option(
    "--index-name",
    required=True,
    help="Elasticsearch index name to convert (required)",
)
@click.option(
    "--backup-file",
    type=click.Path(path_type=Path),
    help="Backup file path before conversion (optional)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without updating Elasticsearch",
)
def convert_elastic(index_name: str, backup_file: Path, dry_run: bool):
    """Convert legacy Elasticsearch documents to new format."""
    converter = LegacyConverter(
        {
            "index_name": index_name,
            "backup_file": backup_file,
            "dry_run": dry_run,
        },
    )

    exit_code = converter.work()
    sys.exit(exit_code)
