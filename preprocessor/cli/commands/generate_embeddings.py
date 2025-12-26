from pathlib import Path
import sys

import click

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import settings
from preprocessor.embeddings.embedding_generator import EmbeddingGenerator


@click.command(name="generate-embeddings")
@click.option(
    "--transcription-jsons",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory with transcription JSON files (required)",
)
@click.option(
    "--frames-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=str(settings.frame_export.output_dir),
    help=f"Directory with exported frames (default: {settings.frame_export.output_dir})",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=str(settings.embedding.default_output_dir),
    help=f"Output directory (default: {settings.embedding.default_output_dir})",
)
@click.option(
    "--model",
    default=settings.embedding.model_name,
    help=f"Model name (default: {settings.embedding.model_name})",
)
@click.option(
    "--segments-per-embedding",
    type=int,
    default=settings.embedding.segments_per_embedding,
    help=f"Segments to group for text embeddings (default: {settings.embedding.segments_per_embedding})",
)
@click.option(
    "--generate-text/--no-text",
    default=True,
    help="Generate text embeddings (default: enabled)",
)
@click.option(
    "--generate-video/--no-video",
    default=True,
    help="Generate video embeddings (default: enabled)",
)
@click.option(
    "--device",
    type=click.Choice(["cuda"]),
    default="cuda",
    help="Device: cuda (GPU only)",
)
@click.option(
    "--batch-size",
    type=int,
    default=settings.embedding.batch_size,
    help=f"Batch size for GPU inference (default: {settings.embedding.batch_size}). Reduce if OOM errors occur",
)
def generate_embeddings(  # pylint: disable=too-many-arguments
    transcription_jsons: Path,
    frames_dir: Path,
    output_dir: Path,
    model: str,
    segments_per_embedding: int,
    generate_text: bool,
    generate_video: bool,
    device: str,
    batch_size: int,
):
    """Generate text and video embeddings from transcriptions and exported frames."""
    with ResourceScope():
        generator = EmbeddingGenerator(
            {
                "transcription_jsons": transcription_jsons,
                "frames_dir": frames_dir,
                "output_dir": output_dir,
                "model": model,
                "segments_per_embedding": segments_per_embedding,
                "generate_text": generate_text,
                "generate_video": generate_video,
                "device": device,
                "batch_size": batch_size,
            },
        )
        exit_code = generator.work()
        generator.cleanup()

    sys.exit(exit_code)
