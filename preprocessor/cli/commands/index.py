from pathlib import Path
import sys

import click

from preprocessor.config.config import IndexConfig
from preprocessor.indexing.elasticsearch import ElasticSearchIndexer


@click.command()
@click.option("--name", required=True, help="Elasticsearch index name")
@click.option(
    "--transcription-jsons",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Directory with transcription JSON files",
)
@click.option("--dry-run", is_flag=True, help="Validate without sending to Elasticsearch")
@click.option("--append", is_flag=True, help="Append to existing index instead of recreating")
def index(name: str, transcription_jsons: Path, dry_run: bool, append: bool):
    """Index transcriptions into Elasticsearch."""
    config = IndexConfig(
        name=name,
        transcription_jsons=transcription_jsons,
        dry_run=dry_run,
        append=append,
    )
    indexer = ElasticSearchIndexer(config.to_dict())
    exit_code = indexer.work()
    sys.exit(exit_code)
