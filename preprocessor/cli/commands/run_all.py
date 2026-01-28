from pathlib import Path
import sys

import click

from preprocessor.cli.pipeline.orchestrator import PipelineOrchestrator
from preprocessor.cli.pipeline.steps import (
    run_archive_generation_step,
    run_character_reference_download_step,
    run_character_reference_processing_step,
    run_character_scrape_step,
    run_elastic_documents_step,
    run_embedding_step,
    run_frame_export_step,
    run_frame_processing_step,
    run_index_step,
    run_scene_step,
    run_scrape_step,
    run_sound_separation_step,
    run_text_analysis_step,
    run_transcode_step,
    run_transcribe_step,
    run_validation_step,
)
from preprocessor.cli.utils import create_state_manager
from preprocessor.config.config import settings
from preprocessor.utils.console import console
from preprocessor.utils.resolution import Resolution


@click.command(context_settings={"show_default": True})
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
    help="Output directory for transcription JSONs",
)
@click.option(
    "--scene-timestamps-dir",
    type=click.Path(path_type=Path),
    default=str(settings.scene_detection.output_dir),
    help="Output directory for scene timestamps",
)
@click.option("--series-name", required=True, help="Series name")
@click.option(
    "--resolution",
    type=click.Choice(Resolution.get_all_choices()),
    default="720p",
    help="Target resolution for transcoding",
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
    help="Whisper model",
)
@click.option(
    "--language",
    default=settings.transcription.language,
    help="Language for transcription",
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
    help="URLs to scrape episode metadata from (Step 0a: optional)",
)
@click.option(
    "--character-urls",
    multiple=True,
    help="URLs to scrape character metadata from (Step 0b: optional)",
)
@click.option(
    "--search-mode",
    type=click.Choice(["normal", "premium"]),
    default="normal",
    help="Image search mode: normal (DuckDuckGo) or premium (Google Images API)",
)
@click.option(
    "--transcription-mode",
    type=click.Choice(["normal", "premium"]),
    default="normal",
    help="Transcription mode: normal (Whisper) or premium (ElevenLabs API)",
)
@click.option(
    "--parser-mode",
    type=click.Choice(["normal", "premium"]),
    default="normal",
    help="Parser mode: normal (Qwen local model) or premium (Gemini 2.5 Flash)",
)
@click.option(
    "--skip-character-reference-processing",
    is_flag=True,
    help="Skip Step 0d: Character reference processing (use existing processed references)",
)
@click.option(
    "--interactive-character-processing",
    is_flag=True,
    help="Enable interactive mode for character reference processing (allows manual face selection)",
)
@click.option("--skip-transcode", is_flag=True, help="Skip Step 1: Transcoding (use existing transcoded videos)")
@click.option("--skip-transcribe", is_flag=True, help="Skip Step 2: Transcription (use existing transcriptions)")
@click.option("--skip-text-analysis", is_flag=True, help="Skip Step 3: Text analysis (use existing text statistics)")
@click.option("--skip-scenes", is_flag=True, help="Skip Step 4: Scene detection (use existing scene timestamps)")
@click.option("--skip-frame-export", is_flag=True, help="Skip Step 5: Frame export (use existing frames)")
@click.option("--skip-embeddings", is_flag=True, help="Skip Step 6: Text embedding generation (use existing text embeddings)")
@click.option("--skip-full-episode", is_flag=True, help="Skip full episode embedding generation (only text, video, sound events)")
@click.option("--skip-image-hashing", is_flag=True, help="Skip Step 7a: Image hashing sub-step (use existing hashes)")
@click.option("--skip-video-embeddings", is_flag=True, help="Skip Step 7b: Video embeddings sub-step (use existing)")
@click.option("--skip-character-detection", is_flag=True, help="Skip Step 7c: Character detection sub-step (use existing)")
@click.option("--skip-emotion-detection", is_flag=True, help="Skip Step 7d: Emotion detection sub-step (use existing)")
@click.option("--skip-face-clustering", is_flag=True, help="Skip Step 7e: Face clustering sub-step (use existing)")
@click.option("--skip-object-detection", is_flag=True, help="Skip Step 7f: Object detection sub-step (use existing)")
@click.option("--debug-visualizations", is_flag=True, help="Enable debug visualizations for character and object detections (disabled by default)")
@click.option("--skip-elastic-documents", is_flag=True, help="Skip Step 8: Generate Elasticsearch documents (use existing documents)")
@click.option("--skip-archives", is_flag=True, help="Skip Step 9: Archive generation (use existing archives)")
@click.option("--skip-index", is_flag=True, help="Skip Step 10: Elasticsearch indexing")
@click.option("--skip-validation", is_flag=True, help="Skip Step 11: Output validation")
def run_all(  # pylint: disable=too-many-arguments,too-many-locals
    videos: Path,
    episodes_info_json: Path,
    transcoded_videos: Path,
    transcription_jsons: Path,
    scene_timestamps_dir: Path,
    series_name: str,
    resolution: str,
    codec: str,
    preset: str,
    model: str,
    language: str,
    dry_run: bool,
    no_state: bool,
    ramdisk_path: Path,
    scrape_urls: tuple,
    character_urls: tuple,
    search_mode: str,
    transcription_mode: str,
    parser_mode: str,
    skip_character_reference_processing: bool,
    interactive_character_processing: bool,
    skip_transcode: bool,
    skip_transcribe: bool,
    skip_text_analysis: bool,
    skip_scenes: bool,
    skip_frame_export: bool,
    skip_embeddings: bool,
    skip_full_episode: bool,
    skip_image_hashing: bool,
    skip_video_embeddings: bool,
    skip_character_detection: bool,
    skip_emotion_detection: bool,
    skip_face_clustering: bool,
    skip_object_detection: bool,
    debug_visualizations: bool,
    skip_elastic_documents: bool,
    skip_archives: bool,
    skip_index: bool,
    skip_validation: bool,
):
    """Run complete video processing pipeline."""
    if transcoded_videos is None:  # pylint: disable=duplicate-code
        transcoded_videos = settings.transcode.output_dir
    if codec is None:
        codec = settings.transcode.codec
    if preset is None:
        preset = settings.transcode.preset

    if scrape_urls and not episodes_info_json:
        episodes_info_json = Path("/app/output_data") / f"{series_name}_episodes.json"

    if not episodes_info_json:
        console.print("[red]Error: Either --episodes-info-json or --scrape-urls must be provided[/red]")
        sys.exit(1)

    characters_json = settings.character.characters_list_file
    if character_urls:
        characters_json = Path("/app/output_data") / f"{series_name}_characters.json"

    state_manager = create_state_manager(series_name, no_state)

    if ramdisk_path:
        console.print(f"[cyan]Using ramdisk: {ramdisk_path}[/cyan]")

    params = {
        "videos": videos,
        "episodes_info_json": episodes_info_json,
        "transcoded_videos": transcoded_videos,
        "transcription_jsons": transcription_jsons,
        "scene_timestamps_dir": scene_timestamps_dir,
        "output_frames": settings.frame_export.output_dir,
        "name": series_name,
        "resolution": resolution,
        "codec": codec,
        "preset": preset,
        "model": model,
        "language": language,
        "device": "cuda",
        "dry_run": dry_run,
        "ramdisk_path": ramdisk_path,
        "scrape_urls": scrape_urls,
        "character_urls": character_urls,
        "characters_json": characters_json,
        "search_mode": search_mode,
        "transcription_mode": transcription_mode,
        "parser_mode": parser_mode,
        "state_manager": state_manager,
        "interactive_character_processing": interactive_character_processing,
        "debug_visualizations": debug_visualizations,
        "skip_image_hashing": skip_image_hashing,
        "skip_video_embeddings": skip_video_embeddings,
        "skip_character_detection": skip_character_detection,
        "skip_character_visualization": not debug_visualizations,
        "skip_emotion_detection": skip_emotion_detection,
        "skip_face_clustering": skip_face_clustering,
        "skip_object_detection": skip_object_detection,
        "skip_object_visualization": not debug_visualizations,
        "skip_full_episode": skip_full_episode,
    }

    metadata_output_dir = Path("/app/output_data/processing_metadata")

    orchestrator = PipelineOrchestrator(
        state_manager=state_manager,
        series_name=series_name,
        metadata_output_dir=metadata_output_dir,
    )
    skip_character_visualization = not debug_visualizations
    skip_object_visualization = not debug_visualizations
    skip_frame_processing = (
        skip_image_hashing and skip_video_embeddings and skip_character_detection
        and skip_character_visualization and skip_emotion_detection and skip_face_clustering
        and skip_object_detection and skip_object_visualization
    )

    orchestrator.add_step("Scraping episode metadata", "0a/14", run_scrape_step, skip=False)
    orchestrator.add_step("Scraping character metadata", "0b/14", run_character_scrape_step, skip=False)
    orchestrator.add_step("Downloading character references", "0c/14", run_character_reference_download_step, skip=False)
    orchestrator.add_step("Processing character references", "0d/14", run_character_reference_processing_step, skip=skip_character_reference_processing)
    orchestrator.add_step("Transcoding videos", "1/14", run_transcode_step, skip=skip_transcode)
    orchestrator.add_step("Generating transcriptions", "2/14", run_transcribe_step, skip=skip_transcribe)
    orchestrator.add_step("Separating sounds and dialogues", "3/14", run_sound_separation_step, skip=skip_transcribe)
    orchestrator.add_step("Analyzing transcription texts", "4/14", run_text_analysis_step, skip=skip_text_analysis)
    orchestrator.add_step("Detecting scenes", "5/14", run_scene_step, skip=skip_scenes)
    orchestrator.add_step("Exporting frames", "6/14", run_frame_export_step, skip=skip_frame_export)
    orchestrator.add_step("Generating text embeddings", "7/14", run_embedding_step, skip=skip_embeddings)
    orchestrator.add_step(
        "Processing frames (hashing + embeddings + characters + emotions + clustering + objects)",
        "8/14",
        run_frame_processing_step,
        skip=skip_frame_processing,
    )
    orchestrator.add_step("Generating Elasticsearch documents", "9/14", run_elastic_documents_step, skip=skip_elastic_documents)
    orchestrator.add_step("Archiving Elasticsearch documents", "10/14", run_archive_generation_step, skip=skip_archives)
    orchestrator.add_step("Indexing in Elasticsearch", "11/14", run_index_step, skip=skip_index)
    orchestrator.add_step("Validating output data", "12/14", run_validation_step, skip=skip_validation)

    exit_code = orchestrator.execute(**params)

    if exit_code == 0:
        console.print("\n[green]All steps completed successfully![/green]")

    sys.exit(exit_code)
