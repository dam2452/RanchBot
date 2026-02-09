from pathlib import Path
import sys

import click

from preprocessor.cli.options.common import (
    episodes_info_option,
    name_option,
)
from preprocessor.config.config import (
    get_base_output_dir,
    settings,
)
from preprocessor.processors.archive_generator import ArchiveGenerator


@click.command(name="generate-archives", context_settings={"show_default": True})
@click.option(
    "--elastic-documents-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Directory with Elasticsearch documents (defaults to {series_name}/elastic_documents)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for ZIP archives (defaults to {series_name}/archives)",
)
@click.option(
    "--season",
    type=int,
    help="Process only specific season",
)
@click.option(
    "--episode",
    type=int,
    help="Process only specific episode (requires --season)",
)
@click.option(
    "--force-regenerate",
    is_flag=True,
    help="Force regenerate existing archives",
)
@click.option(
    "--allow-partial",
    is_flag=True,
    help="Create archives even if not all 5 files are present (default: skip incomplete episodes)",
)
@name_option()
@episodes_info_option(required=False)
def generate_archives(
    elastic_documents_dir: Path,
    output_dir: Path,
    season: int,
    episode: int,
    force_regenerate: bool,
    allow_partial: bool,
    name: str,
    episodes_info_json: Path,
) -> None:
    base_output = get_base_output_dir(name)

    if elastic_documents_dir is None:
        elastic_documents_dir = base_output / settings.output_subdirs.elastic_documents
    if output_dir is None:
        output_dir = base_output / settings.output_subdirs.archives

    args = {
        "elastic_documents_dir": elastic_documents_dir,
        "output_dir": output_dir,
        "series_name": name,
        "episodes_info_json": episodes_info_json,
        "force_regenerate": force_regenerate,
        "allow_partial": allow_partial,
    }

    if season:
        args["season_filter"] = season
    if episode:
        args["episode_filter"] = episode

    generator = ArchiveGenerator(args)
    exit_code = generator.work()
    if exit_code != 0:
        sys.exit(exit_code)
