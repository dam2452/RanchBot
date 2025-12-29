from pathlib import Path

from preprocessor.config.config import settings
from preprocessor.utils.console import console
from preprocessor.video.frame_processor import FrameProcessor
from preprocessor.video.frame_subprocessors import (
    CharacterDetectionSubProcessor,
    ImageHashSubProcessor,
    VideoEmbeddingSubProcessor,
)

# pylint: disable=duplicate-code


def run_scrape_step(scrape_urls, episodes_info_json, videos=None, **_kwargs):
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
            "videos_dir": videos,
        },
    )
    scrape_exit_code = scraper.work()

    if scrape_exit_code != 0:
        console.print("[red]Scraping failed, aborting pipeline[/red]")
        return scrape_exit_code

    console.print(f"[green]Episode metadata saved to: {episodes_info_json}[/green]")
    return 0


def run_character_scrape_step(character_urls, characters_json, name, **_kwargs):
    from preprocessor.scraping.character_scraper import CharacterScraper  # pylint: disable=import-outside-toplevel

    if not character_urls:
        return 0

    if characters_json.exists():
        console.print(
            f"\n[yellow]Scraping character metadata... SKIPPED (file exists: {characters_json})[/yellow]",
        )
        return 0

    scraper = CharacterScraper(
        {
            "urls": list(character_urls),
            "output_file": characters_json,
            "series_name": name,
            "headless": True,
        },
    )
    scrape_exit_code = scraper.work()

    if scrape_exit_code != 0:
        console.print("[red]Character scraping failed[/red]")
        return scrape_exit_code

    console.print(f"[green]Character metadata saved to: {characters_json}[/green]")
    return 0


def run_character_reference_download_step(name, characters_json, search_mode="normal", **_kwargs):
    from preprocessor.characters.reference_downloader import CharacterReferenceDownloader  # pylint: disable=import-outside-toplevel

    if not characters_json.exists():
        console.print("[yellow]No characters.json found, skipping reference download[/yellow]")
        return 0

    downloader = CharacterReferenceDownloader(
        {
            "characters_json": characters_json,
            "series_name": name,
            "output_dir": settings.character.output_dir,
            "images_per_character": settings.character.reference_images_per_character,
            "search_mode": search_mode,
        },
    )
    return downloader.work()


def run_character_detection_step(**kwargs):
    from preprocessor.characters.detector import CharacterDetector  # pylint: disable=import-outside-toplevel

    frames_dir = kwargs.get("output_frames", settings.frame_export.output_dir)
    characters_dir = settings.character.output_dir
    output_dir = settings.character.detections_dir
    episodes_info_json = kwargs.get("episodes_info_json")
    name = kwargs.get("name")
    state_manager = kwargs.get("state_manager")

    detector = CharacterDetector(
        {
            "frames_dir": frames_dir,
            "characters_dir": characters_dir,
            "output_dir": output_dir,
            "episodes_info_json": episodes_info_json,
            "series_name": name,
            "state_manager": state_manager,
        },
    )
    return detector.work()


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


def run_transcribe_step(videos, episodes_info_json, name, model, language, device, ramdisk_path, state_manager, transcription_mode="normal", **kwargs):
    transcription_jsons = kwargs.get("transcription_jsons")

    if transcription_mode == "premium":
        from preprocessor.transcription.elevenlabs import ElevenLabsTranscriber  # pylint: disable=import-outside-toplevel

        console.print("[cyan]Using premium transcription mode (ElevenLabs API)[/cyan]")

        transcriber = ElevenLabsTranscriber(
            {
                "videos": videos,
                "output_dir": transcription_jsons,
                "episodes_info_json": episodes_info_json,
                "series_name": name,
                "api_key": settings.elevenlabs.api_key,
                "model_id": settings.elevenlabs.model_id,
                "language_code": settings.elevenlabs.language_code,
                "diarize": settings.elevenlabs.diarize,
                "state_manager": state_manager,
            },
        )
        return transcriber.work()

    from preprocessor.config.config import TranscriptionConfig  # pylint: disable=import-outside-toplevel
    from preprocessor.transcription.generator import TranscriptionGenerator  # pylint: disable=import-outside-toplevel

    console.print("[cyan]Using normal transcription mode (Whisper)[/cyan]")

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


def run_frame_export_step(state_manager, **kwargs):
    from preprocessor.video.frame_exporter import FrameExporter  # pylint: disable=import-outside-toplevel

    transcoded_videos = kwargs.get("transcoded_videos")
    scene_timestamps_dir = kwargs.get("scene_timestamps_dir")
    name = kwargs.get("name")
    episodes_info_json = kwargs.get("episodes_info_json")
    output_frames = kwargs.get("output_frames", settings.frame_export.output_dir)

    exporter = FrameExporter(
        {
            "transcoded_videos": transcoded_videos,
            "scene_timestamps_dir": scene_timestamps_dir,
            "output_frames": output_frames,
            "frame_height": 480,
            "series_name": name,
            "episodes_info_json": episodes_info_json,
            "state_manager": state_manager,
        },
    )
    return exporter.work()


def run_image_hashing_step(device, state_manager, **kwargs):
    from preprocessor.hashing.image_hash_processor import ImageHashProcessor  # pylint: disable=import-outside-toplevel

    name = kwargs.get("name")
    episodes_info_json = kwargs.get("episodes_info_json")
    frames_dir = kwargs.get("output_frames", settings.frame_export.output_dir)

    hasher = ImageHashProcessor(
        {
            "frames_dir": frames_dir,
            "output_dir": settings.image_hash.output_dir,
            "batch_size": settings.embedding.batch_size,
            "device": device,
            "series_name": name,
            "episodes_info_json": episodes_info_json,
            "state_manager": state_manager,
        },
    )
    exit_code = hasher.work()
    hasher.cleanup()
    return exit_code


def run_embedding_step(device, state_manager, **kwargs):
    from preprocessor.embeddings.embedding_generator import EmbeddingGenerator  # pylint: disable=import-outside-toplevel

    transcription_jsons = kwargs.get("transcription_jsons")
    name = kwargs.get("name")
    episodes_info_json = kwargs.get("episodes_info_json")
    frames_dir = kwargs.get("output_frames", settings.frame_export.output_dir)

    embedding_generator = EmbeddingGenerator(
        {
            "transcription_jsons": transcription_jsons,
            "frames_dir": frames_dir,
            "output_dir": settings.embedding.default_output_dir,
            "image_hashes_dir": settings.image_hash.output_dir,
            "model": settings.embedding.model_name,
            "segments_per_embedding": settings.embedding.segments_per_embedding,
            "generate_text": True,
            "generate_video": False,
            "device": device,
            "batch_size": settings.embedding.batch_size,
            "series_name": name,
            "episodes_info_json": episodes_info_json,
            "state_manager": state_manager,
        },
    )
    exit_code = embedding_generator.work()
    embedding_generator.cleanup()
    return exit_code


def run_elastic_documents_step(**kwargs):
    from preprocessor.indexing.elastic_document_generator import ElasticDocumentGenerator  # pylint: disable=import-outside-toplevel

    transcription_jsons = kwargs.get("transcription_jsons")
    embeddings_dir = settings.embedding.default_output_dir
    scene_timestamps_dir = kwargs.get("scene_timestamps_dir")
    character_detections_dir = settings.character.detections_dir
    name = kwargs.get("name")
    episodes_info_json = kwargs.get("episodes_info_json")

    generator = ElasticDocumentGenerator(
        {
            "transcription_jsons": transcription_jsons,
            "embeddings_dir": embeddings_dir,
            "scene_timestamps_dir": scene_timestamps_dir,
            "character_detections_dir": character_detections_dir,
            "output_dir": Path("/app/output_data/elastic_documents"),
            "series_name": name,
            "episodes_info_json": episodes_info_json,
        },
    )
    return generator.work()


def run_index_step(name, dry_run, state_manager, **kwargs):
    from preprocessor.indexing.elasticsearch import ElasticSearchIndexer  # pylint: disable=import-outside-toplevel

    episodes_info_json = kwargs.get("episodes_info_json")
    elastic_documents_dir = Path("/app/output_data/elastic_documents")

    indexer = ElasticSearchIndexer({
        "name": name,
        "elastic_documents_dir": elastic_documents_dir,
        "dry_run": dry_run,
        "append": False,
        "state_manager": state_manager,
        "series_name": name,
        "episodes_info_json": episodes_info_json,
    })
    return indexer.work()


def run_frame_processing_step(device, state_manager, ramdisk_path, skip_image_hashing, skip_video_embeddings, skip_character_detection, **kwargs):
    name = kwargs.get("name")
    episodes_info_json = kwargs.get("episodes_info_json")
    output_frames = kwargs.get("output_frames", settings.frame_export.output_dir)

    processor = FrameProcessor(
        {
            "frames_dir": output_frames,
            "ramdisk_path": ramdisk_path or Path("/dev/shm"),
            "series_name": name,
            "episodes_info_json": episodes_info_json,
            "state_manager": state_manager,
        },
    )

    sub_processors = []

    if not skip_image_hashing:
        hash_sub = ImageHashSubProcessor(
            device=device,
            batch_size=settings.embedding.batch_size,
        )
        processor.add_sub_processor(hash_sub)
        sub_processors.append(hash_sub)

    if not skip_video_embeddings:
        embedding_sub = VideoEmbeddingSubProcessor(
            device=device,
            batch_size=settings.embedding.batch_size,
            model_name=settings.embedding.model_name,
            model_revision=settings.embedding.model_revision,
            resize_height=settings.embedding.resize_height,
        )
        processor.add_sub_processor(embedding_sub)
        sub_processors.append(embedding_sub)

    if not skip_character_detection:
        char_detection_sub = CharacterDetectionSubProcessor(
            characters_dir=Path(settings.character.output_dir),
            use_gpu=settings.face_recognition.use_gpu,
            threshold=settings.face_recognition.threshold,
        )
        processor.add_sub_processor(char_detection_sub)
        sub_processors.append(char_detection_sub)

    try:
        return processor.work()
    finally:
        for sub in sub_processors:
            sub.cleanup()
