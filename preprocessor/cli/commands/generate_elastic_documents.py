from pathlib import Path
import sys

import click

from preprocessor.cli.options.common import (
    episodes_info_option,
    name_option,
)
from preprocessor.indexing.elastic_document_generator import ElasticDocumentGenerator


@click.command(name="generate-elastic-documents", context_settings={"show_default": True})
@click.option(
    "--transcription-jsons",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory with transcription JSON files",
)
@click.option(
    "--embeddings-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory with embedding files",
)
@click.option(
    "--scene-timestamps-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory with scene timestamp files",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default="/app/output_data/elastic_documents",
    help="Output directory",
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

    generator = ElasticDocumentGenerator(args)
    exit_code = generator.work()
    if exit_code != 0:
        sys.exit(exit_code)
