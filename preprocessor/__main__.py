import sys
from pathlib import Path
from typing import List

import click
from rich.console import Console
from rich.logging import RichHandler

from bot.utils.resolution import Resolution
from preprocessor.config import (
    IndexConfig,
    TranscodeConfig,
    TranscriptionConfig,
)
from preprocessor.elastic_search_indexer import ElasticSearchIndexer
from preprocessor.transciption_generator import TranscriptionGenerator
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
def transcode(videos: Path, transcoded_videos: Path, resolution: str, codec: str, preset: str, crf: int, gop_size: float, episodes_info_json: Path):
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
    transcoder = VideoTranscoder(config.to_dict())
    exit_code = transcoder.work()
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
def transcribe(videos: Path, episodes_info_json: Path, transcription_jsons: Path, model: str, language: str, device: str, extra_json_keys: tuple, name: str):
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
def all(videos: Path, episodes_info_json: Path, transcoded_videos: Path, transcription_jsons: Path, name: str, resolution: str, codec: str, preset: str, model: str, language: str, device: str, dry_run: bool):
    exit_codes: List[int] = []

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
    transcoder = VideoTranscoder(transcode_config.to_dict())
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
    generator = TranscriptionGenerator(transcription_config.to_dict())
    exit_codes.append(generator.work())

    console.print("\n[bold blue]Step 3/3: Indexing in Elasticsearch...[/bold blue]")
    index_config = IndexConfig(
        name=name,
        transcription_jsons=transcription_jsons,
        dry_run=dry_run,
        append=False,
    )
    indexer = ElasticSearchIndexer(index_config.to_dict())
    exit_codes.append(indexer.work())

    sys.exit(max(exit_codes))


if __name__ == "__main__":
    cli()
