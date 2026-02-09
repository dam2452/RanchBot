from pathlib import Path
import sys

import click

from preprocessor.config.config import (
    get_output_path,
    settings,
)
from preprocessor.processors.elasticsearch_indexer import ElasticSearchIndexer


@click.command()
@click.option("--name", required=True, help="Elasticsearch index name (also used as series name for path resolution)")
@click.option(
    "--elastic-documents-dir",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Directory with generated elastic documents",
)
@click.option("--dry-run", is_flag=True, help="Validate without sending to Elasticsearch")
@click.option("--append", is_flag=True, help="Append to existing indices instead of recreating")
def index(name: str, elastic_documents_dir: Path, dry_run: bool, append: bool):
    """Index documents into Elasticsearch (creates 3 indices: segments, text_embeddings, video_frames)."""
    if elastic_documents_dir is None:
        elastic_documents_dir = get_output_path(settings.output_subdirs.elastic_documents, name)

    indexer = ElasticSearchIndexer({
        "name": name,
        "elastic_documents_dir": elastic_documents_dir,
        "dry_run": dry_run,
        "append": append,
    })
    exit_code = indexer.work()
    sys.exit(exit_code)
