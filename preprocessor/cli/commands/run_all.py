from pathlib import Path
import sys

import click

from preprocessor.cli.pipeline.orchestrator import PipelineOrchestrator
from preprocessor.cli.pipeline.steps import (
    run_embedding_step,
    run_index_step,
    run_scene_step,
    run_scrape_step,
    run_transcode_step,
    run_transcribe_step,
)
from preprocessor.cli.utils import create_state_manager
from preprocessor.config.config import settings
from preprocessor.utils.console import console


@click.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--episodes-info-json",
    type=click.Path(path_type=Path),
    help="JSON file with episode metadata (required if not using --scrape-urls)",
)
@click.option(
    "--transcoded-videos",
    type=click.Path(path_type=Path),
    help="Output directory for transcoded videos",
)
@click.option(
    "--transcription-jsons",
    type=click.Path(path_type=Path),
    default=str(settings.transcription.output_dir),
    help=f"Output directory for transcription JSONs (default: {settings.transcription.output_dir})",
)
@click.option(
    "--scene-timestamps-dir",
    type=click.Path(path_type=Path),
    default=str(settings.scene_detection.output_dir),
    help=f"Output directory for scene timestamps (default: {settings.scene_detection.output_dir})",
)
@click.option("--name", required=True, help="Series name (required)")
@click.option(
    "--resolution",
    type=click.Choice(["360p", "480p", "720p", "1080p", "1440p", "2160p"]),
    default="1080p",
    help="Target resolution (default: 1080p)",
)
@click.option(
    "--codec",
    help="Video codec",
)
@click.option(
    "--preset",
    help="FFmpeg preset",
)
@click.option(
    "--model",
    default=settings.transcription.model,
    help=f"Whisper model (default: {settings.transcription.model})",
)
@click.option(
    "--language",
    default=settings.transcription.language,
    help=f"Language for transcription (default: {settings.transcription.language})",
)
@click.option("--dry-run", is_flag=True, help="Dry run for Elasticsearch indexing")
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
@click.option(
    "--ramdisk-path",
    type=click.Path(path_type=Path),
    help="Path to ramdisk for temporary files (e.g., /mnt/ramdisk)",
)
@click.option(
    "--scrape-urls",
    multiple=True,
    help="URLs to scrape episode metadata from (Step 0: optional)",
)
@click.option("--skip-transcode", is_flag=True, help="Skip Step 1: Transcoding (use existing transcoded videos)")
@click.option("--skip-transcribe", is_flag=True, help="Skip Step 2: Transcription (use existing transcriptions)")
@click.option("--skip-scenes", is_flag=True, help="Skip Step 3: Scene detection (use existing scene timestamps)")
@click.option("--skip-embeddings", is_flag=True, help="Skip Step 4: Embedding generation (use existing embeddings)")
@click.option("--skip-index", is_flag=True, help="Skip Step 5: Elasticsearch indexing")
def run_all(  # pylint: disable=too-many-arguments,too-many-locals
    videos: Path,
    episodes_info_json: Path,
    transcoded_videos: Path,
    transcription_jsons: Path,
    scene_timestamps_dir: Path,
    name: str,
    resolution: str,
    codec: str,
    preset: str,
    model: str,
    language: str,
    dry_run: bool,
    no_state: bool,
    ramdisk_path: Path,
    scrape_urls: tuple,
    skip_transcode: bool,
    skip_transcribe: bool,
    skip_scenes: bool,
    skip_embeddings: bool,
    skip_index: bool,
):
    """Run complete video processing pipeline: transcode → transcribe → scenes → embeddings → index."""
    if transcoded_videos is None:  # pylint: disable=duplicate-code
        transcoded_videos = settings.transcode.output_dir
    if codec is None:
        codec = settings.transcode.codec
    if preset is None:
        preset = settings.transcode.preset

    if scrape_urls and not episodes_info_json:
        episodes_info_json = Path("/app/output_data") / f"{name}_episodes.json"

    if not episodes_info_json:
        console.print("[red]Error: Either --episodes-info-json or --scrape-urls must be provided[/red]")
        sys.exit(1)

    state_manager = create_state_manager(name, no_state)

    if ramdisk_path:
        console.print(f"[cyan]Using ramdisk: {ramdisk_path}[/cyan]")

    params = {
        "videos": videos,
        "episodes_info_json": episodes_info_json,
        "transcoded_videos": transcoded_videos,
        "transcription_jsons": transcription_jsons,
        "scene_timestamps_dir": scene_timestamps_dir,
        "name": name,
        "resolution": resolution,
        "codec": codec,
        "preset": preset,
        "model": model,
        "language": language,
        "device": "cuda",
        "dry_run": dry_run,
        "ramdisk_path": ramdisk_path,
        "scrape_urls": scrape_urls,
        "state_manager": state_manager,
    }

    orchestrator = PipelineOrchestrator(state_manager)
    orchestrator.add_step("Scraping episode metadata", "0/5", run_scrape_step, skip=False)
    orchestrator.add_step("Transcoding videos", "1/5", run_transcode_step, skip=skip_transcode)
    orchestrator.add_step("Generating transcriptions", "2/5", run_transcribe_step, skip=skip_transcribe)
    orchestrator.add_step("Detecting scenes", "3/5", run_scene_step, skip=skip_scenes)
    orchestrator.add_step("Generating embeddings", "4/5", run_embedding_step, skip=skip_embeddings)
    orchestrator.add_step("Indexing in Elasticsearch", "5/5", run_index_step, skip=skip_index)

    exit_code = orchestrator.execute(**params)

    if exit_code == 0:
        console.print("\n[green]All steps completed successfully![/green]")

    sys.exit(exit_code)
