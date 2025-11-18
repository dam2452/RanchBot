from pathlib import Path
import sys
from typing import List

import click
from rich.console import Console

from bot.utils.resolution import Resolution
from preprocessor.config import (
    IndexConfig,
    TranscodeConfig,
    TranscriptionConfig,
)
from preprocessor.elevenlabs_transcriber import ElevenLabsTranscriber
from preprocessor.processing.elastic_search_indexer import ElasticSearchIndexer
from preprocessor.processing.embedding_generator import EmbeddingGenerator
from preprocessor.processing.episode_scraper import EpisodeScraper
from preprocessor.processing.legacy_converter import LegacyConverter
from preprocessor.processing.scene_detector import SceneDetector
from preprocessor.state_manager import StateManager
from preprocessor.transcription_generator import TranscriptionGenerator
from preprocessor.transcription_importer import TranscriptionImporter
from preprocessor.video_transcoder import VideoTranscoder

console = Console()


@click.group()
def cli():
    pass


@cli.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--transcoded-videos", type=click.Path(path_type=Path), default=VideoTranscoder.DEFAULT_OUTPUT_DIR)
@click.option("--resolution", type=click.Choice(["360p", "480p", "720p", "1080p", "1440p", "2160p"]), default="1080p")
@click.option("--codec", default=VideoTranscoder.DEFAULT_CODEC)
@click.option("--preset", default=VideoTranscoder.DEFAULT_PRESET)
@click.option("--crf", type=int, default=VideoTranscoder.DEFAULT_CRF)
@click.option("--gop-size", type=float, default=VideoTranscoder.DEFAULT_GOP_SIZE)
@click.option("--episodes-info-json", type=click.Path(exists=True, path_type=Path))
@click.option("--name", help="Series name for state management")
@click.option("--no-state", is_flag=True, help="Disable state management and progress tracking")
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
):
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

    transcoder = VideoTranscoder(config_dict)
    exit_code = transcoder.work()

    if state_manager and exit_code == 0:
        state_manager.cleanup()

    sys.exit(exit_code)


@cli.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--episodes-info-json", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--transcription-jsons", type=click.Path(path_type=Path), default=TranscriptionGenerator.DEFAULT_OUTPUT_DIR)
@click.option("--model", default=TranscriptionGenerator.DEFAULT_MODEL)
@click.option("--language", default=TranscriptionGenerator.DEFAULT_LANGUAGE)
@click.option("--device", default=TranscriptionGenerator.DEFAULT_DEVICE)
@click.option("--extra-json-keys", multiple=True)
@click.option("--name", required=True)
def transcribe(
    videos: Path,
    episodes_info_json: Path,
    transcription_jsons: Path,
    model: str,
    language: str,
    device: str,
    extra_json_keys: tuple,
    name: str,
):
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
    generator = TranscriptionGenerator(config.to_dict())
    exit_code = generator.work()
    sys.exit(exit_code)


@cli.command()
@click.option("--name", required=True)
@click.option("--transcription-jsons", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--dry-run", is_flag=True)
@click.option("--append", is_flag=True)
def index(name: str, transcription_jsons: Path, dry_run: bool, append: bool):
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
@click.option("--source-dir", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True, help="Directory with 11labs transcriptions")
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=TranscriptionGenerator.DEFAULT_OUTPUT_DIR,
    help="Output directory for converted transcriptions",
)
@click.option("--episodes-info-json", type=click.Path(exists=True, path_type=Path), help="Episodes metadata JSON")
@click.option("--name", required=True, help="Series name")
@click.option("--format-type", type=click.Choice(["11labs_segmented", "11labs"]), default="11labs_segmented", help="Source format type")
@click.option("--no-state", is_flag=True, help="Disable state management")
def import_transcriptions(
    source_dir: Path,
    output_dir: Path,
    episodes_info_json: Path,
    name: str,
    format_type: str,
    no_state: bool,
):
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
@click.option("--output-dir", type=click.Path(path_type=Path), default=TranscriptionGenerator.DEFAULT_OUTPUT_DIR, help="Output directory for transcriptions")
@click.option("--episodes-info-json", type=click.Path(exists=True, path_type=Path), help="Episodes metadata JSON")
@click.option("--name", required=True, help="Series name")
@click.option("--api-key", envvar="ELEVEN_API_KEY", help="ElevenLabs API key (or set ELEVEN_API_KEY env var)")
@click.option("--model-id", default="scribe_v1", help="ElevenLabs model ID")
@click.option("--language-code", default="pol", help="Language code")
@click.option("--diarize/--no-diarize", default=True, help="Enable speaker diarization")
@click.option("--no-state", is_flag=True, help="Disable state management")
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
@click.option("--urls", multiple=True, required=True, help="URLs to scrape (can specify multiple times)")
@click.option("--output-file", type=click.Path(path_type=Path), required=True, help="Output JSON file")
@click.option("--llm-provider", type=click.Choice(["lmstudio", "ollama", "gemini"]), default="lmstudio", help="LLM provider")
@click.option("--llm-api-key", envvar="GEMINI_API_KEY", help="API key for LLM (for Gemini)")
@click.option("--llm-model", help="LLM model name (override default)")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
@click.option("--merge-sources/--no-merge", default=True, help="Merge data from multiple sources")
def scrape_episodes(
    urls: tuple,
    output_file: Path,
    llm_provider: str,
    llm_api_key: str,
    llm_model: str,
    headless: bool,
    merge_sources: bool,
):
    scraper = EpisodeScraper({
        "urls": list(urls),
        "output_file": output_file,
        "llm_provider": llm_provider,
        "llm_api_key": llm_api_key,
        "llm_model": llm_model,
        "headless": headless,
        "merge_sources": merge_sources,
    })

    exit_code = scraper.work()
    sys.exit(exit_code)


@cli.command(name="convert-elastic")
@click.option("--index-name", required=True, help="Elasticsearch index name to convert")
@click.option("--backup-file", type=click.Path(path_type=Path), help="Backup file path (optional)")
@click.option("--dry-run", is_flag=True, help="Show what would be converted without updating")
def convert_elastic(index_name: str, backup_file: Path, dry_run: bool):
    converter = LegacyConverter({
        "index_name": index_name,
        "backup_file": backup_file,
        "dry_run": dry_run,
    })

    exit_code = converter.work()
    sys.exit(exit_code)


@cli.command(name="detect-scenes")
@click.argument("videos", type=click.Path(exists=True, path_type=Path))
@click.option("--output-dir", type=click.Path(path_type=Path), default=SceneDetector.DEFAULT_OUTPUT_DIR, help="Output directory for scene JSONs")
@click.option("--threshold", type=float, default=SceneDetector.DEFAULT_THRESHOLD, help="Scene detection threshold")
@click.option("--min-scene-len", type=int, default=SceneDetector.DEFAULT_MIN_SCENE_LEN, help="Minimum scene length in frames")
@click.option("--device", type=click.Choice(["cuda", "cpu"]), default="cuda", help="Device to use")
def detect_scenes(videos: Path, output_dir: Path, threshold: float, min_scene_len: int, device: str):
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
@click.option("--transcription-jsons", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True, help="Directory with transcription JSONs")
@click.option("--videos", type=click.Path(exists=True, path_type=Path), help="Videos directory (for video embeddings)")
@click.option("--output-dir", type=click.Path(path_type=Path), default=EmbeddingGenerator.DEFAULT_OUTPUT_DIR, help="Output directory")
@click.option("--model", default=EmbeddingGenerator.DEFAULT_MODEL, help="Model name")
@click.option(
    "--segments-per-embedding",
    type=int,
    default=EmbeddingGenerator.DEFAULT_SEGMENTS_PER_EMBEDDING,
    help="Segments to group for text embeddings",
)
@click.option(
    "--keyframe-strategy",
    type=click.Choice(["keyframes", "scene_changes", "color_diff"]),
    default=EmbeddingGenerator.DEFAULT_KEYFRAME_STRATEGY,
    help="Video embedding strategy",
)
@click.option("--generate-text/--no-text", default=True, help="Generate text embeddings")
@click.option("--generate-video/--no-video", default=True, help="Generate video embeddings")
@click.option("--device", type=click.Choice(["cuda", "cpu"]), default="cuda", help="Device to use")
@click.option("--scene-timestamps-dir", type=click.Path(path_type=Path), help="Scene timestamps directory (for scene_changes strategy)")
def generate_embeddings(
    transcription_jsons: Path,
    videos: Path,
    output_dir: Path,
    model: str,
    segments_per_embedding: int,
    keyframe_strategy: str,
    generate_text: bool,
    generate_video: bool,
    device: str,
    scene_timestamps_dir: Path,
):
    generator = EmbeddingGenerator({
        "transcription_jsons": transcription_jsons,
        "videos": videos,
        "output_dir": output_dir,
        "model": model,
        "segments_per_embedding": segments_per_embedding,
        "keyframe_strategy": keyframe_strategy,
        "generate_text": generate_text,
        "generate_video": generate_video,
        "device": device,
        "scene_timestamps_dir": scene_timestamps_dir,
    })

    exit_code = generator.work()
    sys.exit(exit_code)


@cli.command()
@click.argument("videos", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--episodes-info-json", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--transcoded-videos", type=click.Path(path_type=Path), default=VideoTranscoder.DEFAULT_OUTPUT_DIR)
@click.option("--transcription-jsons", type=click.Path(path_type=Path), default=TranscriptionGenerator.DEFAULT_OUTPUT_DIR)
@click.option("--name", required=True)
@click.option("--resolution", type=click.Choice(["360p", "480p", "720p", "1080p", "1440p", "2160p"]), default="1080p")
@click.option("--codec", default=VideoTranscoder.DEFAULT_CODEC)
@click.option("--preset", default=VideoTranscoder.DEFAULT_PRESET)
@click.option("--model", default=TranscriptionGenerator.DEFAULT_MODEL)
@click.option("--language", default=TranscriptionGenerator.DEFAULT_LANGUAGE)
@click.option("--device", default=TranscriptionGenerator.DEFAULT_DEVICE)
@click.option("--dry-run", is_flag=True)
@click.option("--no-state", is_flag=True, help="Disable state management and progress tracking")
# pylint: disable=too-many-arguments,too-many-locals
def run_all(
    videos: Path,
    episodes_info_json: Path,
    transcoded_videos: Path,
    transcription_jsons: Path,
    name: str,
    resolution: str,
    codec: str,
    preset: str,
    model: str,
    language: str,
    device: str,
    dry_run: bool,
    no_state: bool,
):
    exit_codes: List[int] = []

    state_manager = None
    if not no_state:
        state_manager = StateManager(series_name=name, working_dir=Path("."))
        state_manager.register_interrupt_handler()
        state_manager.load_or_create_state()

        resume_info = state_manager.get_resume_info()
        if resume_info:
            console.print(f"[cyan]{resume_info}[/cyan]")

    console.print("\n[bold blue]Step 1/3: Transcoding videos...[/bold blue]")
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

    transcoder = VideoTranscoder(transcode_dict)
    exit_codes.append(transcoder.work())

    console.print("\n[bold blue]Step 2/3: Generating transcriptions...[/bold blue]")
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

    generator = TranscriptionGenerator(transcription_dict)
    exit_codes.append(generator.work())

    console.print("\n[bold blue]Step 3/3: Indexing in Elasticsearch...[/bold blue]")
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
