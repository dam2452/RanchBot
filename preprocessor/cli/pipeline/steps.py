from preprocessor.config.config import settings
from preprocessor.utils.console import console

# pylint: disable=duplicate-code


def run_scrape_step(scrape_urls, episodes_info_json, **_kwargs):
    from preprocessor.scraping.episode_scraper import EpisodeScraper  # pylint: disable=import-outside-toplevel

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


def run_transcode_step(videos, episodes_info_json, name, resolution, codec, preset, state_manager, **kwargs):
    from preprocessor.config.config import TranscodeConfig  # pylint: disable=import-outside-toplevel
    from preprocessor.utils.resolution import Resolution  # pylint: disable=import-outside-toplevel
    from preprocessor.video.transcoder import VideoTranscoder  # pylint: disable=import-outside-toplevel

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

    transcoder = VideoTranscoder(transcode_dict)
    return transcoder.work()


def run_transcribe_step(videos, episodes_info_json, name, model, language, device, ramdisk_path, state_manager, **kwargs):
    from preprocessor.config.config import TranscriptionConfig  # pylint: disable=import-outside-toplevel
    from preprocessor.transcription.generator import TranscriptionGenerator  # pylint: disable=import-outside-toplevel

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
    transcription_dict["ramdisk_path"] = ramdisk_path

    generator = TranscriptionGenerator(transcription_dict)
    return generator.work()


def run_scene_step(device, **kwargs):
    from preprocessor.video.scene_detector import SceneDetector  # pylint: disable=import-outside-toplevel

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


def run_embedding_step(device, **kwargs):
    from preprocessor.embeddings.generator import EmbeddingGenerator  # pylint: disable=import-outside-toplevel

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


def run_elastic_documents_step(**kwargs):
    from pathlib import Path  # pylint: disable=import-outside-toplevel
    from preprocessor.indexing.elastic_document_generator import ElasticDocumentGenerator  # pylint: disable=import-outside-toplevel

    transcription_jsons = kwargs.get("transcription_jsons")
    embeddings_dir = settings.embedding.default_output_dir
    scene_timestamps_dir = kwargs.get("scene_timestamps_dir")
    name = kwargs.get("name")
    episodes_info_json = kwargs.get("episodes_info_json")

    generator = ElasticDocumentGenerator(
        {
            "transcription_jsons": transcription_jsons,
            "embeddings_dir": embeddings_dir,
            "scene_timestamps_dir": scene_timestamps_dir,
            "output_dir": Path("/app/output_data/elastic_documents"),
            "series_name": name,
            "episodes_info_json": episodes_info_json,
        },
    )
    return generator.work()


def run_index_step(name, dry_run, state_manager, **kwargs):
    from preprocessor.config.config import IndexConfig  # pylint: disable=import-outside-toplevel
    from preprocessor.indexing.elasticsearch import ElasticSearchIndexer  # pylint: disable=import-outside-toplevel

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
