from pathlib import Path
import sys
from typing import List

import click

from preprocessor.cli_utils.resource_scope import ResourceScope
from preprocessor.config.config import settings
from preprocessor.core.state_manager import StateManager
from preprocessor.utils.console import console


@click.group()
@click.help_option("-h", "--help")
def cli():
    pass


@cli.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--transcoded-videos",
    type=click.Path(path_type=Path),
    default=str(settings.transcode.output_dir),
    help=f"Output directory for transcoded videos (default: {settings.transcode.output_dir})",
)
@click.option(
    "--resolution",
    type=click.Choice(["360p", "480p", "720p", "1080p", "1440p", "2160p"]),
    default="1080p",
    help="Target resolution for videos (default: 1080p)",
)
@click.option(
    "--codec",
    help="Video codec: h264_nvenc (GPU), libx264 (CPU)",
)
@click.option(
    "--preset",
    help="FFmpeg preset: slow, medium, fast",
)
@click.option(
    "--crf",
    type=int,
    help="Quality (CRF): 0=best 51=worst, 18-28 recommended",
)
@click.option(
    "--gop-size",
    type=float,
    help="Keyframe interval in seconds",
)
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    help="JSON file with episode metadata",
)
@click.option("--name", help="Series name for state management and resume support")
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
@click.option(
    "--max-workers",
    type=int,
    help="Number of parallel workers",
)
# pylint: disable=too-many-arguments,too-many-locals,import-outside-toplevel
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
    from bot.utils.resolution import Resolution
    from preprocessor.config.config import TranscodeConfig
    from preprocessor.video.transcoder import VideoTranscoder

    if transcoded_videos is None:
        transcoded_videos = settings.transcode.output_dir
    if codec is None:
        codec = settings.transcode.codec
    if preset is None:
        preset = settings.transcode.preset
    if crf is None:
        crf = settings.transcode.crf
    if gop_size is None:
        gop_size = settings.transcode.gop_size
    if max_workers is None:
        max_workers = settings.transcode.max_workers

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

    with ResourceScope():
        transcoder = VideoTranscoder(config_dict)
        exit_code = transcoder.work()

    if state_manager and exit_code == 0:
        state_manager.cleanup()

    sys.exit(exit_code)


@cli.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="JSON file with episode metadata (required)",
)
@click.option(
    "--transcription-jsons",
    type=click.Path(path_type=Path),
    default=str(settings.transcription.output_dir),
    help=f"Output directory for transcription JSONs (default: {settings.transcription.output_dir})",
)
@click.option(
    "--model",
    default=settings.transcription.model,
    help=f"Whisper model: tiny, base, small, medium, large, large-v3-turbo (default: {settings.transcription.model})",
)
@click.option(
    "--language",
    default=settings.transcription.language,
    help=f"Language for transcription (default: {settings.transcription.language})",
)
@click.option(
    "--device",
    default=settings.transcription.device,
    help=f"Device: cuda (GPU) or cpu (default: {settings.transcription.device})",
)
@click.option(
    "--extra-json-keys",
    multiple=True,
    help="Additional JSON keys to remove from output (can specify multiple times)",
)
@click.option(
    "--name",
    required=True,
    help="Series name for output files (required)",
)
@click.option(
    "--max-workers",
    type=int,
    default=1,
    help="Number of parallel workers for audio normalization (default: 1)",
)
# pylint: disable=import-outside-toplevel
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
    from preprocessor.config.config import TranscriptionConfig
    from preprocessor.transcription.generator import TranscriptionGenerator

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

    with ResourceScope():
        generator = TranscriptionGenerator(config_dict)
        exit_code = generator.work()

    sys.exit(exit_code)


@cli.command()
@click.option("--name", required=True, help="Elasticsearch index name (required)")
@click.option(
    "--transcription-jsons",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Directory with transcription JSON files (required)",
)
@click.option("--dry-run", is_flag=True, help="Validate without sending to Elasticsearch")
@click.option("--append", is_flag=True, help="Append to existing index instead of recreating")
# pylint: disable=import-outside-toplevel
def index(name: str, transcription_jsons: Path, dry_run: bool, append: bool):
    from preprocessor.config.config import IndexConfig
    from preprocessor.indexing.elasticsearch import ElasticSearchIndexer

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
    "--source-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory with source transcriptions (11labs format)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=str(settings.transcription.output_dir),
    help=f"Output directory for converted transcriptions (default: {settings.transcription.output_dir})",
)
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    help="JSON file with episode metadata (optional)",
)
@click.option("--name", required=True, help="Series name (required)")
@click.option(
    "--format-type",
    type=click.Choice(["11labs_segmented", "11labs"]),
    default="11labs_segmented",
    help="Source format: 11labs_segmented or 11labs (default: 11labs_segmented)",
)
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
# pylint: disable=import-outside-toplevel
def import_transcriptions(
    source_dir: Path,
    output_dir: Path,
    episodes_info_json: Path,
    name: str,
    format_type: str,
    no_state: bool,
):
    from preprocessor.transcription.importer import TranscriptionImporter

    state_manager = None
    if not no_state:
        state_manager = StateManager(series_name=name, working_dir=Path("."))
        state_manager.register_interrupt_handler()
        state_manager.load_or_create_state()

        resume_info = state_manager.get_resume_info()
        if resume_info:
            console.print(f"[cyan]{resume_info}[/cyan]")

    importer = TranscriptionImporter(
        {
            "source_dir": source_dir,
            "output_dir": output_dir,
            "episodes_info_json": episodes_info_json,
            "series_name": name,
            "format_type": format_type,
            "state_manager": state_manager,
        },
    )

    exit_code = importer.work()

    if state_manager and exit_code == 0:
        console.print("[green]Import completed successfully![/green]")
        state_manager.cleanup()

    sys.exit(exit_code)


@cli.command(name="transcribe-elevenlabs")
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=str(settings.transcription.output_dir),
    help=f"Output directory for transcriptions (default: {settings.transcription.output_dir})",
)
@click.option(
    "--episodes-info-json",
    type=click.Path(exists=True, path_type=Path),
    help="JSON file with episode metadata (optional)",
)
@click.option("--name", required=True, help="Series name (required)")
@click.option(
    "--api-key",
    envvar="ELEVEN_API_KEY",
    help="ElevenLabs API key (or set ELEVEN_API_KEY env var)",
)
@click.option(
    "--model-id",
    default="scribe_v1",
    help="ElevenLabs model ID (default: scribe_v1)",
)
@click.option(
    "--language-code",
    default="pol",
    help="Language code: pol, eng, etc (default: pol)",
)
@click.option(
    "--diarize/--no-diarize",
    default=True,
    help="Enable speaker diarization (default: enabled)",
)
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
# pylint: disable=import-outside-toplevel
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
    from preprocessor.transcription.elevenlabs import ElevenLabsTranscriber

    state_manager = None
    if not no_state:
        state_manager = StateManager(series_name=name, working_dir=Path("."))
        state_manager.register_interrupt_handler()
        state_manager.load_or_create_state()

        resume_info = state_manager.get_resume_info()
        if resume_info:
            console.print(f"[cyan]{resume_info}[/cyan]")

    transcriber = ElevenLabsTranscriber(
        {
            "videos": videos,
            "output_dir": output_dir,
            "episodes_info_json": episodes_info_json,
            "series_name": name,
            "api_key": api_key,
            "model_id": model_id,
            "language_code": language_code,
            "diarize": diarize,
            "state_manager": state_manager,
        },
    )

    exit_code = transcriber.work()

    if state_manager and exit_code == 0:
        console.print("[green]Transcription completed successfully![/green]")
        state_manager.cleanup()

    sys.exit(exit_code)


@cli.command(name="scrape-episodes")
@click.option(
    "--urls",
    multiple=True,
    required=True,
    help="URL to scrape (specify multiple times for multiple sources)",
)
@click.option(
    "--output-file",
    type=click.Path(path_type=Path),
    required=True,
    help="Output JSON file path (required)",
)
@click.option(
    "--headless/--no-headless",
    default=True,
    help="Run browser in headless mode (default: enabled)",
)
@click.option(
    "--merge-sources/--no-merge",
    default=True,
    help="Merge data from multiple sources (default: enabled)",
)
# pylint: disable=import-outside-toplevel
def scrape_episodes(
    urls: tuple,
    output_file: Path,
    headless: bool,
    merge_sources: bool,
):
    from preprocessor.scraping.episode_scraper import EpisodeScraper

    scraper = EpisodeScraper(
        {
            "urls": list(urls),
            "output_file": output_file,
            "headless": headless,
            "merge_sources": merge_sources,
        },
    )

    exit_code = scraper.work()
    sys.exit(exit_code)


@cli.command(name="convert-elastic")
@click.option(
    "--index-name",
    required=True,
    help="Elasticsearch index name to convert (required)",
)
@click.option(
    "--backup-file",
    type=click.Path(path_type=Path),
    help="Backup file path before conversion (optional)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without updating Elasticsearch",
)
# pylint: disable=import-outside-toplevel
def convert_elastic(index_name: str, backup_file: Path, dry_run: bool):
    from preprocessor.legacy.legacy_converter import LegacyConverter

    converter = LegacyConverter(
        {
            "index_name": index_name,
            "backup_file": backup_file,
            "dry_run": dry_run,
        },
    )

    exit_code = converter.work()
    sys.exit(exit_code)


@cli.command(name="detect-scenes")
@click.argument("videos", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=str(settings.scene_detection.output_dir),
    help=f"Output directory for scene JSON files (default: {settings.scene_detection.output_dir})",
)
@click.option(
    "--threshold",
    type=float,
    default=settings.scene_detection.threshold,
    help=f"Scene detection threshold 0.0-1.0 (default: {settings.scene_detection.threshold})",
)
@click.option(
    "--min-scene-len",
    type=int,
    default=settings.scene_detection.min_scene_len,
    help=f"Minimum scene length in frames (default: {settings.scene_detection.min_scene_len})",
)
# pylint: disable=import-outside-toplevel
def detect_scenes(videos: Path, output_dir: Path, threshold: float, min_scene_len: int):
    from preprocessor.video.scene_detector import SceneDetector

    with ResourceScope():
        detector = SceneDetector(
            {
                "videos": videos,
                "output_dir": output_dir,
                "threshold": threshold,
                "min_scene_len": min_scene_len,
            },
        )
        exit_code = detector.work()
        detector.cleanup()

    sys.exit(exit_code)


@cli.command(name="generate-embeddings")
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
# pylint: disable=too-many-arguments,import-outside-toplevel
def generate_embeddings(
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
    from preprocessor.embeddings.generator import EmbeddingGenerator

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


# pylint: disable=import-outside-toplevel
def _run_scrape_step(scrape_urls, episodes_info_json, **_kwargs):
    from preprocessor.scraping.episode_scraper import EpisodeScraper

    if not scrape_urls:
        return 0

    if episodes_info_json.exists():
        console.print(
            f"\n[yellow]Scraping episode metadata... SKIPPED (file exists: {episodes_info_json})[/yellow]",
        )
        return 0

    scraper = EpisodeScraper(
        {
            "urls": list(scrape_urls),
            "output_file": episodes_info_json,
            "headless": True,
            "merge_sources": True,
        },
    )
    scrape_exit_code = scraper.work()

    if scrape_exit_code != 0:
        console.print("[red]Scraping failed, aborting pipeline[/red]")
        return scrape_exit_code

    console.print(f"[green]Episode metadata saved to: {episodes_info_json}[/green]")
    return 0


# pylint: disable=import-outside-toplevel
def _run_transcode_step(videos, episodes_info_json, name, resolution, codec, preset, max_workers, state_manager, **kwargs):
    from bot.utils.resolution import Resolution
    from preprocessor.config.config import TranscodeConfig
    from preprocessor.video.transcoder import VideoTranscoder

    transcoded_videos = kwargs.get("transcoded_videos")

    transcode_config = TranscodeConfig(
        videos=videos,
        transcoded_videos=transcoded_videos,
        resolution=Resolution.from_str(resolution),
        codec=codec,
        preset=preset,
        crf=settings.transcode.crf,
        gop_size=settings.transcode.gop_size,
        episodes_info_json=episodes_info_json,
    )
    transcode_dict = transcode_config.to_dict()
    transcode_dict["state_manager"] = state_manager
    transcode_dict["series_name"] = name
    transcode_dict["max_workers"] = max_workers

    transcoder = VideoTranscoder(transcode_dict)
    return transcoder.work()


# pylint: disable=import-outside-toplevel
def _run_transcribe_step(videos, episodes_info_json, name, model, language, device, max_workers, ramdisk_path, state_manager, **kwargs):
    from preprocessor.config.config import TranscriptionConfig
    from preprocessor.transcription.generator import TranscriptionGenerator

    transcription_jsons = kwargs.get("transcription_jsons")

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
    return generator.work()


# pylint: disable=import-outside-toplevel
def _run_scene_step(device, **kwargs):
    from preprocessor.video.scene_detector import SceneDetector

    transcoded_videos = kwargs.get("transcoded_videos")
    scene_timestamps_dir = kwargs.get("scene_timestamps_dir")
    name = kwargs.get("name")
    episodes_info_json = kwargs.get("episodes_info_json")

    detector = SceneDetector(
        {
            "videos": transcoded_videos,
            "output_dir": scene_timestamps_dir,
            "threshold": settings.scene_detection.threshold,
            "min_scene_len": settings.scene_detection.min_scene_len,
            "device": device,
            "series_name": name,
            "episodes_info_json": episodes_info_json,
        },
    )
    exit_code = detector.work()
    detector.cleanup()
    return exit_code


# pylint: disable=import-outside-toplevel
def _run_embedding_step(device, **kwargs):
    from preprocessor.embeddings.generator import EmbeddingGenerator

    transcription_jsons = kwargs.get("transcription_jsons")
    transcoded_videos = kwargs.get("transcoded_videos")
    scene_timestamps_dir = kwargs.get("scene_timestamps_dir")
    name = kwargs.get("name")
    episodes_info_json = kwargs.get("episodes_info_json")

    embedding_generator = EmbeddingGenerator(
        {
            "transcription_jsons": transcription_jsons,
            "videos": transcoded_videos,
            "output_dir": settings.embedding.default_output_dir,
            "model": settings.embedding.model_name,
            "segments_per_embedding": settings.embedding.segments_per_embedding,
            "keyframe_strategy": "scene_changes",
            "keyframe_interval": settings.embedding.keyframe_interval,
            "frames_per_scene": settings.embedding.frames_per_scene,
            "generate_text": True,
            "generate_video": True,
            "device": device,
            "batch_size": settings.embedding.batch_size,
            "scene_timestamps_dir": scene_timestamps_dir,
            "series_name": name,
            "episodes_info_json": episodes_info_json,
        },
    )
    exit_code = embedding_generator.work()
    embedding_generator.cleanup()
    return exit_code


# pylint: disable=import-outside-toplevel
def _run_index_step(name, dry_run, state_manager, **kwargs):
    from preprocessor.config.config import IndexConfig
    from preprocessor.indexing.elasticsearch import ElasticSearchIndexer

    transcription_jsons = kwargs.get("transcription_jsons")
    episodes_info_json = kwargs.get("episodes_info_json")

    index_config = IndexConfig(
        name=name,
        transcription_jsons=transcription_jsons,
        dry_run=dry_run,
        append=False,
    )
    index_dict = index_config.to_dict()
    index_dict["state_manager"] = state_manager
    index_dict["series_name"] = name
    index_dict["episodes_info_json"] = episodes_info_json

    indexer = ElasticSearchIndexer(index_dict)
    return indexer.work()


@cli.command()
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
@click.option(
    "--device",
    default=settings.transcription.device,
    help=f"Device: cuda or cpu (default: {settings.transcription.device})",
)
@click.option("--dry-run", is_flag=True, help="Dry run for Elasticsearch indexing")
@click.option("--no-state", is_flag=True, help="Disable state management (no resume on interrupt)")
@click.option(
    "--max-workers",
    type=int,
    default=1,
    help="Number of parallel workers per step for processing multiple episodes (default: 1)",
)
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
# pylint: disable=too-many-arguments,too-many-locals,import-outside-toplevel
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
    ramdisk_path: Path,
    scrape_urls: tuple,
    skip_transcode: bool,
    skip_transcribe: bool,
    skip_scenes: bool,
    skip_embeddings: bool,
    skip_index: bool,
):
    if transcoded_videos is None:
        transcoded_videos = settings.transcode.output_dir
    if codec is None:
        codec = settings.transcode.codec
    if preset is None:
        preset = settings.transcode.preset

    exit_codes: List[int] = []

    if scrape_urls and not episodes_info_json:
        episodes_info_json = Path("/app/output_data") / f"{name}_episodes.json"

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
        "device": device,
        "dry_run": dry_run,
        "max_workers": max_workers,
        "ramdisk_path": ramdisk_path,
        "scrape_urls": scrape_urls,
        "state_manager": state_manager,
    }

    steps = [
        ("Scraping episode metadata", _run_scrape_step, False, "0/5"),
        ("Transcoding videos", _run_transcode_step, skip_transcode, "1/5"),
        ("Generating transcriptions", _run_transcribe_step, skip_transcribe, "2/5"),
        ("Detecting scenes", _run_scene_step, skip_scenes, "3/5"),
        ("Generating embeddings", _run_embedding_step, skip_embeddings, "4/5"),
        ("Indexing in Elasticsearch", _run_index_step, skip_index, "5/5"),
    ]

    for step_name, step_func, should_skip, step_num in steps:
        if should_skip:
            console.print(f"\n[yellow]Step {step_num}: {step_name}... SKIPPED[/yellow]")
            continue

        console.print(f"\n[bold blue]Step {step_num}: {step_name}...[/bold blue]")

        with ResourceScope():
            exit_code = step_func(**params)

        exit_codes.append(exit_code)

        if exit_code != 0:
            console.print(f"[red]Pipeline failed at step: {step_name}[/red]")
            sys.exit(exit_code)

    if state_manager and (not exit_codes or max(exit_codes) == 0):
        console.print("\n[green]All steps completed successfully![/green]")
        state_manager.cleanup()

    sys.exit(max(exit_codes) if exit_codes else 0)


if __name__ == "__main__":
    cli()
