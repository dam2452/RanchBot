from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from pathlib import Path
import sys
from typing import List

import click
from rich.console import Console

from bot.utils.resolution import Resolution
from preprocessor.config.config import (
    IndexConfig,
    TranscodeConfig,
    TranscriptionConfig,
)
from preprocessor.core.state_manager import StateManager
from preprocessor.processing.elastic_search_indexer import ElasticSearchIndexer
from preprocessor.processing.embedding_generator import EmbeddingGenerator
from preprocessor.processing.episode_scraper import EpisodeScraper
from preprocessor.processing.legacy.legacy_converter import LegacyConverter
from preprocessor.processing.scene_detector import SceneDetector
from preprocessor.transcriptions.elevenlabs_transcriber import ElevenLabsTranscriber
from preprocessor.transcriptions.transcription_generator import TranscriptionGenerator
from preprocessor.transcriptions.transcription_importer import TranscriptionImporter
from preprocessor.video.video_transcoder import VideoTranscoder

console = Console()


@click.group()
@click.help_option("-h", "--help")
def cli():
    """
    Video preprocessing pipeline for Ranczo Klipy Bot.

    Transcode videos, generate transcriptions (Whisper/ElevenLabs),
    detect scenes, generate embeddings, and index in Elasticsearch.

    \b
    Quick Start:
      # Full pipeline (all steps)
      python -m preprocessor run-all /videos --episodes-info-json episodes.json --name ranczo

      # Step by step
      python -m preprocessor transcode /videos --episodes-info-json episodes.json
      python -m preprocessor transcribe /videos --episodes-info-json episodes.json --name ranczo
      python -m preprocessor index --name ranczo --transcription-jsons ./transcriptions

    \b
    Use --help on any command for detailed options:
      python -m preprocessor transcode --help
    """


@cli.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--transcoded-videos", type=click.Path(path_type=Path), default=VideoTranscoder.DEFAULT_OUTPUT_DIR,
    help=f"Output directory for transcoded videos (default: {VideoTranscoder.DEFAULT_OUTPUT_DIR})",
)
@click.option(
    "--resolution", type=click.Choice(["360p", "480p", "720p", "1080p", "1440p", "2160p"]), default="1080p",
    help="Target resolution for videos (default: 1080p)",
)
@click.option(
    "--codec", default=VideoTranscoder.DEFAULT_CODEC,
    help=f"Video codec: h264_nvenc (GPU), libx264 (CPU) (default: {VideoTranscoder.DEFAULT_CODEC})",
)
@click.option(
    "--preset", default=VideoTranscoder.DEFAULT_PRESET,
    help=f"FFmpeg preset: slow, medium, fast (default: {VideoTranscoder.DEFAULT_PRESET})",
)
@click.option(
    "--crf", type=int, default=VideoTranscoder.DEFAULT_CRF,
    help=f"Quality (CRF): 0=best 51=worst, 18-28 recommended (default: {VideoTranscoder.DEFAULT_CRF})",
)
@click.option(
    "--gop-size", type=float, default=VideoTranscoder.DEFAULT_GOP_SIZE,
    help=f"Keyframe interval in seconds (default: {VideoTranscoder.DEFAULT_GOP_SIZE}s)",
)
@click.option(
    "--episodes-info-json", type=click.Path(exists=True, path_type=Path),
    help="JSON file with episode metadata",
)
@click.option("--name", help="Series name for state management and resume support")
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
@click.option(
    "--max-workers", type=int, default=VideoTranscoder.DEFAULT_MAX_WORKERS,
    help=f"Number of parallel workers (default: {VideoTranscoder.DEFAULT_MAX_WORKERS})",
)
# pylint: disable=too-many-arguments
def transcode(
    videos: Path,
    transcoded_videos: Path,
    resolution: str,
    codec: str,
    preset: str,
    crf: int,
    gop_size: float,
    episodes_info_json: Path,
    name: str,
    no_state: bool,
    max_workers: int,
):
    """
    Transcode videos to standardized format with keyframes.

    Converts videos to uniform resolution/codec for optimal bot performance.
    Uses FFmpeg with GPU acceleration (NVENC) if available.

    \b
    Example:
      python -m preprocessor transcode /videos --episodes-info-json episodes.json --name ranczo
      python -m preprocessor transcode /videos --resolution 720p --codec libx264 --crf 23
    """
    state_manager = None
    if not no_state and name:
        state_manager = StateManager(series_name=name, working_dir=Path("."))
        state_manager.register_interrupt_handler()
        state_manager.load_or_create_state()

        resume_info = state_manager.get_resume_info()
        if resume_info:
            console.print(f"[cyan]{resume_info}[/cyan]")

    config = TranscodeConfig(
        videos=videos,
        transcoded_videos=transcoded_videos,
        resolution=Resolution.from_str(resolution),
        codec=codec,
        preset=preset,
        crf=crf,
        gop_size=gop_size,
        episodes_info_json=episodes_info_json,
    )
    config_dict = config.to_dict()
    config_dict["state_manager"] = state_manager
    config_dict["series_name"] = name or "unknown"
    config_dict["max_workers"] = max_workers

    transcoder = VideoTranscoder(config_dict)
    exit_code = transcoder.work()

    if state_manager and exit_code == 0:
        state_manager.cleanup()

    sys.exit(exit_code)


@cli.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--episodes-info-json", type=click.Path(exists=True, path_type=Path), required=True,
    help="JSON file with episode metadata (required)",
)
@click.option(
    "--transcription-jsons", type=click.Path(path_type=Path), default=TranscriptionGenerator.DEFAULT_OUTPUT_DIR,
    help=f"Output directory for transcription JSONs (default: {TranscriptionGenerator.DEFAULT_OUTPUT_DIR})",
)
@click.option(
    "--model", default=TranscriptionGenerator.DEFAULT_MODEL,
    help=f"Whisper model: tiny, base, small, medium, large, large-v3-turbo (default: {TranscriptionGenerator.DEFAULT_MODEL})",
)
@click.option(
    "--language", default=TranscriptionGenerator.DEFAULT_LANGUAGE,
    help=f"Language for transcription (default: {TranscriptionGenerator.DEFAULT_LANGUAGE})",
)
@click.option(
    "--device", default=TranscriptionGenerator.DEFAULT_DEVICE,
    help=f"Device: cuda (GPU) or cpu (default: {TranscriptionGenerator.DEFAULT_DEVICE})",
)
@click.option(
    "--extra-json-keys", multiple=True,
    help="Additional JSON keys to remove from output (can specify multiple times)",
)
@click.option(
    "--name", required=True,
    help="Series name for output files (required)",
)
@click.option(
    "--max-workers", type=int, default=1,
    help="Number of parallel workers for audio normalization (default: 1)",
)
def transcribe(
    videos: Path,
    episodes_info_json: Path,
    transcription_jsons: Path,
    model: str,
    language: str,
    device: str,
    extra_json_keys: tuple,
    name: str,
    max_workers: int,
):
    """
    Generate audio transcriptions using OpenAI Whisper.

    Extracts audio, normalizes it, and transcribes using Whisper.
    GPU acceleration recommended (10-50x faster than CPU).

    \b
    Models (speed vs accuracy):
      tiny, base     - Fast but less accurate
      small, medium  - Balanced
      large, large-v3-turbo - Most accurate (recommended)

    \b
    Example:
      python -m preprocessor transcribe /videos --episodes-info-json episodes.json --name ranczo
      python -m preprocessor transcribe /videos --episodes-info-json episodes.json --name ranczo --model base --device cpu
    """
    config = TranscriptionConfig(
        videos=videos,
        episodes_info_json=episodes_info_json,
        transcription_jsons=transcription_jsons,
        model=model,
        language=language,
        device=device,
        extra_json_keys_to_remove=list(extra_json_keys),
        name=name,
    )
    config_dict = config.to_dict()
    config_dict["max_workers"] = max_workers
    generator = TranscriptionGenerator(config_dict)
    exit_code = generator.work()
    sys.exit(exit_code)


@cli.command()
@click.option("--name", required=True, help="Elasticsearch index name (required)")
@click.option(
    "--transcription-jsons", type=click.Path(exists=True, path_type=Path), required=True,
    help="Directory with transcription JSON files (required)",
)
@click.option("--dry-run", is_flag=True, help="Validate without sending to Elasticsearch")
@click.option("--append", is_flag=True, help="Append to existing index instead of recreating")
def index(name: str, transcription_jsons: Path, dry_run: bool, append: bool):
    """
    Index transcriptions in Elasticsearch for full-text search.

    Creates or updates Elasticsearch index with transcription segments.
    Requires Elasticsearch running on localhost:9200.

    \b
    Example:
      python -m preprocessor index --name ranczo --transcription-jsons ./transcriptions
      python -m preprocessor index --name ranczo --transcription-jsons ./transcriptions --append
      python -m preprocessor index --name ranczo --transcription-jsons ./transcriptions --dry-run
    """
    config = IndexConfig(
        name=name,
        transcription_jsons=transcription_jsons,
        dry_run=dry_run,
        append=append,
    )
    indexer = ElasticSearchIndexer(config.to_dict())
    exit_code = indexer.work()
    sys.exit(exit_code)


@cli.command(name="import-transcriptions")
@click.option(
    "--source-dir", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True,
    help="Directory with source transcriptions (11labs format)",
)
@click.option(
    "--output-dir", type=click.Path(path_type=Path), default=TranscriptionGenerator.DEFAULT_OUTPUT_DIR,
    help=f"Output directory for converted transcriptions (default: {TranscriptionGenerator.DEFAULT_OUTPUT_DIR})",
)
@click.option(
    "--episodes-info-json", type=click.Path(exists=True, path_type=Path),
    help="JSON file with episode metadata (optional)",
)
@click.option("--name", required=True, help="Series name (required)")
@click.option(
    "--format-type", type=click.Choice(["11labs_segmented", "11labs"]), default="11labs_segmented",
    help="Source format: 11labs_segmented or 11labs (default: 11labs_segmented)",
)
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
def import_transcriptions(
    source_dir: Path,
    output_dir: Path,
    episodes_info_json: Path,
    name: str,
    format_type: str,
    no_state: bool,
):
    """
    Import existing transcriptions (ElevenLabs format).

    Converts pre-generated transcriptions to standard format.
    Much faster and cheaper than re-transcribing.

    \b
    Example:
      python -m preprocessor import-transcriptions --source-dir ./11labs_output --name ranczo --episodes-info-json episodes.json
      python -m preprocessor import-transcriptions --source-dir ./11labs --name kapitan_bomba --format-type 11labs
    """
    state_manager = None
    if not no_state:
        state_manager = StateManager(series_name=name, working_dir=Path("."))
        state_manager.register_interrupt_handler()
        state_manager.load_or_create_state()

        resume_info = state_manager.get_resume_info()
        if resume_info:
            console.print(f"[cyan]{resume_info}[/cyan]")

    importer = TranscriptionImporter({
        "source_dir": source_dir,
        "output_dir": output_dir,
        "episodes_info_json": episodes_info_json,
        "series_name": name,
        "format_type": format_type,
        "state_manager": state_manager,
    })

    exit_code = importer.work()

    if state_manager and exit_code == 0:
        console.print("[green]Import completed successfully![/green]")
        state_manager.cleanup()

    sys.exit(exit_code)


@cli.command(name="transcribe-elevenlabs")
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--output-dir", type=click.Path(path_type=Path), default=TranscriptionGenerator.DEFAULT_OUTPUT_DIR,
    help=f"Output directory for transcriptions (default: {TranscriptionGenerator.DEFAULT_OUTPUT_DIR})",
)
@click.option(
    "--episodes-info-json", type=click.Path(exists=True, path_type=Path),
    help="JSON file with episode metadata (optional)",
)
@click.option("--name", required=True, help="Series name (required)")
@click.option(
    "--api-key", envvar="ELEVEN_API_KEY",
    help="ElevenLabs API key (or set ELEVEN_API_KEY env var)",
)
@click.option(
    "--model-id", default="scribe_v1",
    help="ElevenLabs model ID (default: scribe_v1)",
)
@click.option(
    "--language-code", default="pol",
    help="Language code: pol, eng, etc (default: pol)",
)
@click.option(
    "--diarize/--no-diarize", default=True,
    help="Enable speaker diarization (default: enabled)",
)
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
def transcribe_elevenlabs(
    videos: Path,
    output_dir: Path,
    episodes_info_json: Path,
    name: str,
    api_key: str,
    model_id: str,
    language_code: str,
    diarize: bool,
    no_state: bool,
):
    """
    Generate transcriptions using ElevenLabs API.

    High-quality transcriptions with speaker diarization.
    Requires ElevenLabs API key.

    \b
    Example:
      export ELEVEN_API_KEY=your_api_key
      python -m preprocessor transcribe-elevenlabs /videos --name ranczo --episodes-info-json episodes.json
      python -m preprocessor transcribe-elevenlabs /videos --name ranczo --api-key sk-xxx --language-code eng
    """
    state_manager = None
    if not no_state:
        state_manager = StateManager(series_name=name, working_dir=Path("."))
        state_manager.register_interrupt_handler()
        state_manager.load_or_create_state()

        resume_info = state_manager.get_resume_info()
        if resume_info:
            console.print(f"[cyan]{resume_info}[/cyan]")

    transcriber = ElevenLabsTranscriber({
        "videos": videos,
        "output_dir": output_dir,
        "episodes_info_json": episodes_info_json,
        "series_name": name,
        "api_key": api_key,
        "model_id": model_id,
        "language_code": language_code,
        "diarize": diarize,
        "state_manager": state_manager,
    })

    exit_code = transcriber.work()

    if state_manager and exit_code == 0:
        console.print("[green]Transcription completed successfully![/green]")
        state_manager.cleanup()

    sys.exit(exit_code)


@cli.command(name="scrape-episodes")
@click.option(
    "--urls", multiple=True, required=True,
    help="URL to scrape (specify multiple times for multiple sources)",
)
@click.option(
    "--output-file", type=click.Path(path_type=Path), required=True,
    help="Output JSON file path (required)",
)
@click.option(
    "--llm-provider", type=click.Choice(["lmstudio", "ollama", "gemini"]), default="lmstudio",
    help="LLM provider: lmstudio, ollama, gemini (default: lmstudio)",
)
@click.option("--llm-model", help="LLM model name (override default for provider)")
@click.option(
    "--headless/--no-headless", default=True,
    help="Run browser in headless mode (default: enabled)",
)
@click.option(
    "--merge-sources/--no-merge", default=True,
    help="Merge data from multiple sources (default: enabled)",
)
def scrape_episodes(
    urls: tuple,
    output_file: Path,
    llm_provider: str,
    llm_model: str,
    headless: bool,
    merge_sources: bool,
):
    """
    Scrape episode metadata from web pages using LLM.

    Uses Playwright to extract page content and LLM to structure data.
    Supports multiple sources for cross-referencing.

    \b
    Example:
      python -m preprocessor scrape-episodes --urls https://filmweb.pl/serial/Ranczo-2006/season/1/episode/1 --output-file metadata.json
      python -m preprocessor scrape-episodes --urls https://filmweb.pl/... --urls https://wikipedia.org/... --output-file metadata.json
      export GEMINI_API_KEY=your_key
      python -m preprocessor scrape-episodes --urls https://example.com --output-file metadata.json --llm-provider gemini
    """
    scraper = EpisodeScraper({
        "urls": list(urls),
        "output_file": output_file,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "headless": headless,
        "merge_sources": merge_sources,
    })

    exit_code = scraper.work()
    sys.exit(exit_code)


@cli.command(name="convert-elastic")
@click.option(
    "--index-name", required=True,
    help="Elasticsearch index name to convert (required)",
)
@click.option(
    "--backup-file", type=click.Path(path_type=Path),
    help="Backup file path before conversion (optional)",
)
@click.option(
    "--dry-run", is_flag=True,
    help="Preview changes without updating Elasticsearch",
)
def convert_elastic(index_name: str, backup_file: Path, dry_run: bool):
    """
    Convert legacy Elasticsearch index to new format.

    Ad-hoc script for one-time migration. Adds missing fields
    and converts old structure to new format.

    \b
    Example:
      python -m preprocessor convert-elastic --index-name ranczo --dry-run
      python -m preprocessor convert-elastic --index-name ranczo --backup-file backup.json
    """
    converter = LegacyConverter({
        "index_name": index_name,
        "backup_file": backup_file,
        "dry_run": dry_run,
    })

    exit_code = converter.work()
    sys.exit(exit_code)


@cli.command(name="detect-scenes")
@click.argument("videos", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir", type=click.Path(path_type=Path), default=SceneDetector.DEFAULT_OUTPUT_DIR,
    help=f"Output directory for scene JSON files (default: {SceneDetector.DEFAULT_OUTPUT_DIR})",
)
@click.option(
    "--threshold", type=float, default=SceneDetector.DEFAULT_THRESHOLD,
    help=f"Scene detection threshold 0.0-1.0 (default: {SceneDetector.DEFAULT_THRESHOLD})",
)
@click.option(
    "--min-scene-len", type=int, default=SceneDetector.DEFAULT_MIN_SCENE_LEN,
    help=f"Minimum scene length in frames (default: {SceneDetector.DEFAULT_MIN_SCENE_LEN})",
)
@click.option(
    "--device", type=click.Choice(["cuda", "cpu"]), default="cuda",
    help="Device: cuda (GPU) or cpu (default: cuda)",
)
def detect_scenes(videos: Path, output_dir: Path, threshold: float, min_scene_len: int, device: str):
    """
    Detect scene cuts in videos using TransNetV2 or histogram.

    Identifies scene changes and outputs timestamps.
    GPU acceleration recommended for TransNetV2.

    \b
    Example:
      python -m preprocessor detect-scenes /videos
      python -m preprocessor detect-scenes video.mp4 --threshold 0.3 --min-scene-len 15
      python -m preprocessor detect-scenes /videos --device cpu
    """
    detector = SceneDetector({
        "videos": videos,
        "output_dir": output_dir,
        "threshold": threshold,
        "min_scene_len": min_scene_len,
        "device": device,
    })

    exit_code = detector.work()
    sys.exit(exit_code)


@cli.command(name="generate-embeddings")
@click.option(
    "--transcription-jsons", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True,
    help="Directory with transcription JSON files (required)",
)
@click.option(
    "--videos", type=click.Path(exists=True, path_type=Path),
    help="Videos directory for video embeddings (optional)",
)
@click.option(
    "--output-dir", type=click.Path(path_type=Path), default=EmbeddingGenerator.DEFAULT_OUTPUT_DIR,
    help=f"Output directory (default: {EmbeddingGenerator.DEFAULT_OUTPUT_DIR})",
)
@click.option(
    "--model", default=EmbeddingGenerator.DEFAULT_MODEL,
    help=f"Model name (default: {EmbeddingGenerator.DEFAULT_MODEL})",
)
@click.option(
    "--segments-per-embedding", type=int, default=EmbeddingGenerator.DEFAULT_SEGMENTS_PER_EMBEDDING,
    help=f"Segments to group for text embeddings (default: {EmbeddingGenerator.DEFAULT_SEGMENTS_PER_EMBEDDING})",
)
@click.option(
    "--keyframe-strategy", type=click.Choice(["keyframes", "scene_changes", "color_diff"]),
    default=EmbeddingGenerator.DEFAULT_KEYFRAME_STRATEGY,
    help=f"Strategy: keyframes (every 5s), scene_changes, color_diff (default: {EmbeddingGenerator.DEFAULT_KEYFRAME_STRATEGY})",
)
@click.option(
    "--keyframe-interval", type=int, default=EmbeddingGenerator.DEFAULT_KEYFRAME_INTERVAL,
    help=f"Extract every Nth keyframe/scene (default: {EmbeddingGenerator.DEFAULT_KEYFRAME_INTERVAL})",
)
@click.option(
    "--generate-text/--no-text", default=True,
    help="Generate text embeddings (default: enabled)",
)
@click.option(
    "--generate-video/--no-video", default=True,
    help="Generate video embeddings (default: enabled)",
)
@click.option(
    "--device", type=click.Choice(["cuda", "cpu"]), default="cuda",
    help="Device: cuda (GPU) or cpu (default: cuda)",
)
@click.option(
    "--max-workers", type=int, default=EmbeddingGenerator.DEFAULT_MAX_WORKERS,
    help=f"Number of parallel workers for processing episodes (default: {EmbeddingGenerator.DEFAULT_MAX_WORKERS})",
)
@click.option(
    "--batch-size", type=int, default=EmbeddingGenerator.DEFAULT_BATCH_SIZE,
    help=f"Batch size for GPU inference (default: {EmbeddingGenerator.DEFAULT_BATCH_SIZE})",
)
@click.option(
    "--scene-timestamps-dir", type=click.Path(path_type=Path),
    help="Scene timestamps directory (for scene_changes strategy)",
)
# pylint: disable=too-many-arguments
def generate_embeddings(
    transcription_jsons: Path,
    videos: Path,
    output_dir: Path,
    model: str,
    segments_per_embedding: int,
    keyframe_strategy: str,
    keyframe_interval: int,
    generate_text: bool,
    generate_video: bool,
    device: str,
    max_workers: int,
    batch_size: int,
    scene_timestamps_dir: Path,
):
    """
    Generate text and video embeddings for semantic search.

    Creates embeddings from transcriptions and video keyframes using GPU-accelerated
    batch inference with Decord video decoder. For scene_changes strategy, extracts
    3 frames per scene (start, mid, end) for better representation.

    \b
    Strategies:
      keyframes      - Extract every 5 seconds
      scene_changes  - Use scene timestamps, 3 frames per scene (recommended)
      color_diff     - Detect color/histogram changes

    \b
    Performance Tips:
      - Use --batch-size 24-32 for RTX 3090 (24GB VRAM)
      - Set --max-workers 1 for single GPU (model uses ~16GB VRAM)
      - scene_changes strategy with Decord provides 5-10x speedup vs OpenCV

    \b
    Example:
      python -m preprocessor generate-embeddings --transcription-jsons ./transcriptions --videos ./videos
      python -m preprocessor generate-embeddings --transcription-jsons ./transcriptions --videos ./videos --batch-size 32
      python -m preprocessor generate-embeddings --transcription-jsons ./transcriptions --videos ./videos \
          --keyframe-interval 2 --scene-timestamps-dir ./scene_timestamps
    """
    generator = EmbeddingGenerator({
        "transcription_jsons": transcription_jsons,
        "videos": videos,
        "output_dir": output_dir,
        "model": model,
        "segments_per_embedding": segments_per_embedding,
        "keyframe_strategy": keyframe_strategy,
        "keyframe_interval": keyframe_interval,
        "generate_text": generate_text,
        "generate_video": generate_video,
        "device": device,
        "max_workers": max_workers,
        "batch_size": batch_size,
        "scene_timestamps_dir": scene_timestamps_dir,
    })

    exit_code = generator.work()
    sys.exit(exit_code)


@cli.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--episodes-info-json", type=click.Path(path_type=Path),
    help="JSON file with episode metadata (required if not using --scrape-urls)",
)
@click.option(
    "--transcoded-videos", type=click.Path(path_type=Path), default=VideoTranscoder.DEFAULT_OUTPUT_DIR,
    help=f"Output directory for transcoded videos (default: {VideoTranscoder.DEFAULT_OUTPUT_DIR})",
)
@click.option(
    "--transcription-jsons", type=click.Path(path_type=Path), default=TranscriptionGenerator.DEFAULT_OUTPUT_DIR,
    help=f"Output directory for transcription JSONs (default: {TranscriptionGenerator.DEFAULT_OUTPUT_DIR})",
)
@click.option(
    "--scene-timestamps-dir", type=click.Path(path_type=Path), default=SceneDetector.DEFAULT_OUTPUT_DIR,
    help=f"Output directory for scene timestamps (default: {SceneDetector.DEFAULT_OUTPUT_DIR})",
)
@click.option("--name", required=True, help="Series name (required)")
@click.option(
    "--resolution", type=click.Choice(["360p", "480p", "720p", "1080p", "1440p", "2160p"]), default="1080p",
    help="Target resolution (default: 1080p)",
)
@click.option(
    "--codec", default=VideoTranscoder.DEFAULT_CODEC,
    help=f"Video codec (default: {VideoTranscoder.DEFAULT_CODEC})",
)
@click.option(
    "--preset", default=VideoTranscoder.DEFAULT_PRESET,
    help=f"FFmpeg preset (default: {VideoTranscoder.DEFAULT_PRESET})",
)
@click.option(
    "--model", default=TranscriptionGenerator.DEFAULT_MODEL,
    help=f"Whisper model (default: {TranscriptionGenerator.DEFAULT_MODEL})",
)
@click.option(
    "--language", default=TranscriptionGenerator.DEFAULT_LANGUAGE,
    help=f"Language for transcription (default: {TranscriptionGenerator.DEFAULT_LANGUAGE})",
)
@click.option(
    "--device", default=TranscriptionGenerator.DEFAULT_DEVICE,
    help=f"Device: cuda or cpu (default: {TranscriptionGenerator.DEFAULT_DEVICE})",
)
@click.option("--dry-run", is_flag=True, help="Dry run for Elasticsearch indexing")
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
@click.option(
    "--max-workers", type=int, default=1,
    help="Number of parallel workers per step (default: 1)",
)
@click.option(
    "--parallel-steps/--no-parallel-steps", default=True,
    help="Run transcribe and scene detection in parallel (default: enabled)",
)
@click.option(
    "--ramdisk-path", type=click.Path(path_type=Path),
    help="Path to ramdisk for temporary files (e.g., /mnt/ramdisk)",
)
@click.option(
    "--scrape-urls", multiple=True,
    help="URLs to scrape episode metadata from (Step 0: optional)",
)
@click.option(
    "--llm-provider", type=click.Choice(["lmstudio", "ollama", "gemini"]), default="ollama",
    help="LLM provider for scraping (default: ollama)",
)
# pylint: disable=too-many-arguments,too-many-locals,too-many-statements
def run_all(
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
    device: str,
    dry_run: bool,
    no_state: bool,
    max_workers: int,
    parallel_steps: bool,
    ramdisk_path: Path,
    scrape_urls: tuple,
    llm_provider: str,
):
    """
    Run complete pipeline: [scrape] → transcode → [transcribe || scenes] → embeddings → index.

    Optimized for high-end systems (64GB RAM, RTX 3090).
    By default runs transcribe and scene detection in parallel.

    \b
    Steps:
      0. [Optional] Scrape episode metadata from URLs
      1. Transcode videos (NVENC GPU)
      2. [Transcribe (Whisper) || Scene Detection (TransNetV2)] - parallel
      3. Generate embeddings (batch + decord)
      4. Index to Elasticsearch

    \b
    Performance optimizations:
      - Parallel transcribe + scene detection (saves ~30-40% time)
      - Optional ramdisk for temp files (with 64GB RAM)
      - Batch embeddings with Decord (5-10x faster)
      - Multi-worker support for each step

    \b
    Example:
      # With existing episodes.json:
      python -m preprocessor run-all /videos --episodes-info-json episodes.json --name ranczo

      # Scrape metadata first:
      python -m preprocessor run-all /videos --name ranczo \
          --scrape-urls https://filmweb.pl/... \
          --scrape-urls https://wikipedia.org/...

      # With all optimizations:
      python -m preprocessor run-all /videos --episodes-info-json episodes.json --name ranczo \
          --ramdisk-path /mnt/ramdisk --parallel-steps
    """
    exit_codes: List[int] = []

    if scrape_urls and not episodes_info_json:
        episodes_info_json = Path(f"{name}_episodes.json")

    if not episodes_info_json:
        console.print("[red]Error: Either --episodes-info-json or --scrape-urls must be provided[/red]")
        sys.exit(1)

    state_manager = None
    if not no_state:
        state_manager = StateManager(series_name=name, working_dir=Path("."))
        state_manager.register_interrupt_handler()
        state_manager.load_or_create_state()

        resume_info = state_manager.get_resume_info()
        if resume_info:
            console.print(f"[cyan]{resume_info}[/cyan]")

    if ramdisk_path:
        console.print(f"[cyan]Using ramdisk: {ramdisk_path}[/cyan]")

    if scrape_urls:
        console.print("\n[bold blue]Step 0/5: Scraping episode metadata...[/bold blue]")
        scraper = EpisodeScraper({
            "urls": list(scrape_urls),
            "output_file": episodes_info_json,
            "llm_provider": llm_provider,
            "llm_model": None,
            "headless": True,
            "merge_sources": True,
        })
        scrape_exit_code = scraper.work()
        exit_codes.append(scrape_exit_code)

        if scrape_exit_code != 0:
            console.print("[red]Scraping failed, aborting pipeline[/red]")
            sys.exit(scrape_exit_code)

        console.print(f"[green]Episode metadata saved to: {episodes_info_json}[/green]")

    console.print("\n[bold blue]Step 1/5: Transcoding videos...[/bold blue]")
    transcode_config = TranscodeConfig(
        videos=videos,
        transcoded_videos=transcoded_videos,
        resolution=Resolution.from_str(resolution),
        codec=codec,
        preset=preset,
        crf=VideoTranscoder.DEFAULT_CRF,
        gop_size=VideoTranscoder.DEFAULT_GOP_SIZE,
        episodes_info_json=episodes_info_json,
    )
    transcode_dict = transcode_config.to_dict()
    transcode_dict["state_manager"] = state_manager
    transcode_dict["series_name"] = name
    transcode_dict["max_workers"] = max_workers

    transcoder = VideoTranscoder(transcode_dict)
    exit_codes.append(transcoder.work())

    if parallel_steps:
        console.print("\n[bold blue]Step 2/5: Running transcription + scene detection in parallel...[/bold blue]")

        transcription_config = TranscriptionConfig(
            videos=videos,
            episodes_info_json=episodes_info_json,
            transcription_jsons=transcription_jsons,
            model=model,
            language=language,
            device=device,
            extra_json_keys_to_remove=[],
            name=name,
        )
        transcription_dict = transcription_config.to_dict()
        transcription_dict["state_manager"] = state_manager
        transcription_dict["series_name"] = name
        transcription_dict["max_workers"] = max_workers
        transcription_dict["ramdisk_path"] = ramdisk_path

        scene_detector_args = {
            "videos": transcoded_videos,
            "output_dir": scene_timestamps_dir,
            "threshold": SceneDetector.DEFAULT_THRESHOLD,
            "min_scene_len": SceneDetector.DEFAULT_MIN_SCENE_LEN,
            "device": device,
        }

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_transcribe = executor.submit(
                lambda: TranscriptionGenerator(transcription_dict).work(),
            )
            future_scenes = executor.submit(
                lambda: SceneDetector(scene_detector_args).work(),
            )

            results = {}
            for future in as_completed([future_transcribe, future_scenes]):
                try:
                    result = future.result()
                    if future == future_transcribe:
                        console.print("[green]Transcription completed[/green]")
                        results['transcribe'] = result
                    else:
                        console.print("[green]Scene detection completed[/green]")
                        results['scenes'] = result
                except (RuntimeError, ValueError, OSError) as e:
                    console.print(f"[red]Error in parallel step: {e}[/red]")
                    exit_codes.append(1)

        exit_codes.append(results.get('transcribe', 0))
        exit_codes.append(results.get('scenes', 0))

    else:
        console.print("\n[bold blue]Step 2/5: Generating transcriptions...[/bold blue]")
        transcription_config = TranscriptionConfig(
            videos=videos,
            episodes_info_json=episodes_info_json,
            transcription_jsons=transcription_jsons,
            model=model,
            language=language,
            device=device,
            extra_json_keys_to_remove=[],
            name=name,
        )
        transcription_dict = transcription_config.to_dict()
        transcription_dict["state_manager"] = state_manager
        transcription_dict["series_name"] = name
        transcription_dict["max_workers"] = max_workers
        transcription_dict["ramdisk_path"] = ramdisk_path

        generator = TranscriptionGenerator(transcription_dict)
        exit_codes.append(generator.work())

        console.print("\n[bold blue]Step 3/5: Detecting scenes...[/bold blue]")
        detector = SceneDetector({
            "videos": transcoded_videos,
            "output_dir": scene_timestamps_dir,
            "threshold": SceneDetector.DEFAULT_THRESHOLD,
            "min_scene_len": SceneDetector.DEFAULT_MIN_SCENE_LEN,
            "device": device,
        })
        exit_codes.append(detector.work())

    console.print("\n[bold blue]Step 4/5: Generating embeddings...[/bold blue]")
    embedding_generator = EmbeddingGenerator({
        "transcription_jsons": transcription_jsons,
        "videos": transcoded_videos,
        "output_dir": EmbeddingGenerator.DEFAULT_OUTPUT_DIR,
        "model": EmbeddingGenerator.DEFAULT_MODEL,
        "segments_per_embedding": EmbeddingGenerator.DEFAULT_SEGMENTS_PER_EMBEDDING,
        "keyframe_strategy": "scene_changes",
        "keyframe_interval": EmbeddingGenerator.DEFAULT_KEYFRAME_INTERVAL,
        "generate_text": True,
        "generate_video": True,
        "device": device,
        "max_workers": 1,
        "batch_size": EmbeddingGenerator.DEFAULT_BATCH_SIZE,
        "scene_timestamps_dir": scene_timestamps_dir,
    })
    exit_codes.append(embedding_generator.work())

    console.print("\n[bold blue]Step 5/5: Indexing in Elasticsearch...[/bold blue]")
    index_config = IndexConfig(
        name=name,
        transcription_jsons=transcription_jsons,
        dry_run=dry_run,
        append=False,
    )
    index_dict = index_config.to_dict()
    index_dict["state_manager"] = state_manager
    index_dict["series_name"] = name

    indexer = ElasticSearchIndexer(index_dict)
    exit_codes.append(indexer.work())

    if state_manager and max(exit_codes) == 0:
        console.print("\n[green]All steps completed successfully![/green]")
        state_manager.cleanup()

    sys.exit(max(exit_codes))


if __name__ == "__main__":
    cli()
