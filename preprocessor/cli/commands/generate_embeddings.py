from pathlib import Path
import sys

import click

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import settings
from preprocessor.embeddings.generator import EmbeddingGenerator


@click.command(name="generate-embeddings")
@click.option(
    "--transcription-jsons",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory with transcription JSON files (required)",
)
@click.option(
    "--videos",
    type=click.Path(exists=True, path_type=Path),
    help="Videos directory for video embeddings (optional)",
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
    "--keyframe-strategy",
    type=click.Choice(["keyframes", "scene_changes", "color_diff"]),
    default=settings.embedding.keyframe_strategy,
    help=f"Strategy: keyframes (simple every 5s), scene_changes (smart from scenes), color_diff (default: {settings.embedding.keyframe_strategy})",
)
@click.option(
    "--keyframe-interval",
    type=int,
    default=settings.embedding.keyframe_interval,
    help=f"For 'keyframes' strategy: extract every Nth keyframe (1=all, 2=every 2nd) (default: {settings.embedding.keyframe_interval})",
)
@click.option(
    "--frames-per-scene",
    type=int,
    default=settings.embedding.frames_per_scene,
    help=f"For 'scene_changes' strategy: frames per scene (3, 5, 7, etc.) (default: {settings.embedding.frames_per_scene})",
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
@click.option(
    "--scene-timestamps-dir",
    type=click.Path(path_type=Path),
    help="Scene timestamps directory (for scene_changes strategy)",
)
def generate_embeddings(  # pylint: disable=too-many-arguments
    transcription_jsons: Path,
    videos: Path,
    output_dir: Path,
    model: str,
    segments_per_embedding: int,
    keyframe_strategy: str,
    keyframe_interval: int,
    frames_per_scene: int,
    generate_text: bool,
    generate_video: bool,
    device: str,
    batch_size: int,
    scene_timestamps_dir: Path,
):
    """Generate text and video embeddings from transcriptions."""
    with ResourceScope():
        generator = EmbeddingGenerator(
            {
                "transcription_jsons": transcription_jsons,
                "videos": videos,
                "output_dir": output_dir,
                "model": model,
                "segments_per_embedding": segments_per_embedding,
                "keyframe_strategy": keyframe_strategy,
                "keyframe_interval": keyframe_interval,
                "frames_per_scene": frames_per_scene,
                "generate_text": generate_text,
                "generate_video": generate_video,
                "device": device,
                "batch_size": batch_size,
                "scene_timestamps_dir": scene_timestamps_dir,
            },
        )
        exit_code = generator.work()
        generator.cleanup()

    sys.exit(exit_code)
