from pathlib import Path
import sys

import click

from preprocessor.cli.options.common import (
    episodes_info_option,
    name_option,
)
from preprocessor.config.config import settings
from preprocessor.indexing.elastic_document_generator import ElasticDocumentGenerator


@click.command(name="generate-elastic-documents")
@click.option(
    "--transcription-jsons",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory with transcription JSON files (required)",
)
@click.option(
    "--embeddings-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory with embedding files (optional)",
)
@click.option(
    "--scene-timestamps-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory with scene timestamp files (optional)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default="/app/output_data/elastic_documents",
    help="Output directory (default: /app/output_data/elastic_documents)",
)
@name_option()
@episodes_info_option(required=False)
def generate_elastic_documents(
    transcription_jsons: Path,
    embeddings_dir: Path,
    scene_timestamps_dir: Path,
    output_dir: Path,
    name: str,
    episodes_info_json: Path,
) -> None:
    args = {
        "transcription_jsons": transcription_jsons,
        "embeddings_dir": embeddings_dir,
        "scene_timestamps_dir": scene_timestamps_dir,
        "output_dir": output_dir,
        "series_name": name,
        "episodes_info_json": episodes_info_json,
    }

    try:
        generator = ElasticDocumentGenerator(args)
        generator()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
