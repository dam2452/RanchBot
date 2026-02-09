from pathlib import Path
import sys

import click

from preprocessor.cli.options.common import (
    episodes_info_option,
    name_option,
)
from preprocessor.config.config import (
    get_output_path,
    settings,
)
from preprocessor.processors.elastic_document_generator import ElasticDocumentGenerator


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
    "--character-detections-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory with character detection files",
)
@click.option(
    "--object-detections-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory with object detection files",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory",
)
@name_option()
@episodes_info_option(required=False)
def generate_elastic_documents(
    transcription_jsons: Path,
    embeddings_dir: Path,
    scene_timestamps_dir: Path,
    character_detections_dir: Path,
    object_detections_dir: Path,
    output_dir: Path,
    name: str,
    episodes_info_json: Path,
) -> None:
    if output_dir is None:
        output_dir = get_output_path(settings.output_subdirs.elastic_documents, name)
    args = {
        "transcription_jsons": transcription_jsons,
        "embeddings_dir": embeddings_dir,
        "scene_timestamps_dir": scene_timestamps_dir,
        "character_detections_dir": character_detections_dir,
        "object_detections_dir": object_detections_dir,
        "output_dir": output_dir,
        "series_name": name,
        "episodes_info_json": episodes_info_json,
    }

    generator = ElasticDocumentGenerator(args)
    exit_code = generator.work()
    if exit_code != 0:
        sys.exit(exit_code)
