from pathlib import Path
import sys

import click

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import settings
from preprocessor.embeddings.embedding_generator import EmbeddingGenerator


@click.command(name="generate-embeddings", context_settings={"show_default": True})
@click.option(
    "--transcription-jsons",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory with transcription JSON files",
)
@click.option(
    "--frames-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=str(settings.frame_export.output_dir),
    help="Directory with exported frames",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=str(settings.embedding.default_output_dir),
    help="Output directory",
)
@click.option(
    "--image-hashes-dir",
    type=click.Path(path_type=Path),
    default=str(settings.image_hash.output_dir),
    help="Directory with image hashes",
)
@click.option(
    "--model",
    default=settings.embedding_model.model_name,
    help="Model name",
)
@click.option(
    "--segments-per-embedding",
    type=int,
    default=settings.text_chunking.segments_per_embedding,
    help="Segments to group for text embeddings",
)
@click.option(
    "--generate-text/--no-text",
    default=True,
    help="Generate text embeddings",
)
@click.option(
    "--generate-video/--no-video",
    default=True,
    help="Generate video embeddings",
)
@click.option(
    "--generate-episode-names/--no-episode-names",
    default=True,
    help="Generate episode name embeddings",
)
@click.option(
    "--generate-full-episode/--no-full-episode",
    default=True,
    help="Generate full episode embeddings",
)
@click.option(
    "--generate-sound-events/--no-sound-events",
    default=True,
    help="Generate sound event embeddings",
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
    help="Batch size for GPU inference. Reduce if OOM errors occur",
)
@click.option(
    "--sentence-chunking/--segment-chunking",
    default=settings.text_chunking.use_sentence_based_chunking,
    help="Use sentence-based chunking (smart, with overlap) or segment-based chunking (simple)",
)
@click.option(
    "--sentences-per-chunk",
    type=int,
    default=settings.text_chunking.text_sentences_per_chunk,
    help="Number of sentences per chunk (only for --sentence-chunking)",
)
@click.option(
    "--chunk-overlap",
    type=int,
    default=settings.text_chunking.text_chunk_overlap,
    help="Number of overlapping sentences between chunks (only for --sentence-chunking)",
)
def generate_embeddings(  # pylint: disable=too-many-arguments,too-many-locals
    transcription_jsons: Path,
    frames_dir: Path,
    output_dir: Path,
    image_hashes_dir: Path,
    model: str,
    segments_per_embedding: int,
    generate_text: bool,
    generate_video: bool,
    generate_episode_names: bool,
    generate_full_episode: bool,
    generate_sound_events: bool,
    device: str,
    batch_size: int,
    sentence_chunking: bool,
    sentences_per_chunk: int,
    chunk_overlap: int,
):
    """Generate text and video embeddings from transcriptions and exported frames."""
    with ResourceScope():
        generator = EmbeddingGenerator(
            {
                "transcription_jsons": transcription_jsons,
                "frames_dir": frames_dir,
                "output_dir": output_dir,
                "image_hashes_dir": image_hashes_dir,
                "model": model,
                "segments_per_embedding": segments_per_embedding,
                "generate_text": generate_text,
                "generate_video": generate_video,
                "generate_episode_names": generate_episode_names,
                "generate_full_episode": generate_full_episode,
                "generate_sound_events": generate_sound_events,
                "device": device,
                "batch_size": batch_size,
                "use_sentence_based_chunking": sentence_chunking,
                "text_sentences_per_chunk": sentences_per_chunk,
                "text_chunk_overlap": chunk_overlap,
            },
        )
        exit_code = generator.work()
        generator.cleanup()

    sys.exit(exit_code)
