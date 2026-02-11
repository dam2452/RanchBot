from typing import Dict

from preprocessor.app.pipeline import Pipeline
from preprocessor.app.step_builder import (
    Phase,
    StepBuilder,
)
from preprocessor.config.config import get_base_output_dir
from preprocessor.config.series_config import SeriesConfig
from preprocessor.config.step_configs import (
    ArchiveConfig,
    CharacterDetectionConfig,
    CharacterReferenceConfig,
    CharacterScraperConfig,
    DocumentGenerationConfig,
    ElasticsearchConfig,
    EmotionDetectionConfig,
    EpisodeScraperConfig,
    FaceClusteringConfig,
    FrameExportConfig,
    ImageHashConfig,
    ObjectDetectionConfig,
    SceneDetectionConfig,
    SoundSeparationConfig,
    TextAnalysisConfig,
    TextEmbeddingConfig,
    TranscodeConfig,
    VideoEmbeddingConfig,
    WhisperTranscriptionConfig,
)

SCRAPING = Phase("SCRAPING", color="blue")
PROCESSING = Phase("PROCESSING", color="green")
INDEXING = Phase("INDEXING", color="yellow")


def build_pipeline(series_name: str) -> Pipeline:  # pylint: disable=too-many-locals
    series_config: SeriesConfig = SeriesConfig.load(series_name)

    episodes_metadata = StepBuilder(
        id="scrape_episodes",
        phase=SCRAPING,
        module="preprocessor.modules.scraping.episode_scraper_step:EpisodeScraperStep",
        description="Scrapes episode metadata from wiki",
        produces=["episodes.json"],
        needs=[],
        config=EpisodeScraperConfig(
            urls=series_config.scraping.episodes.urls,
            output_file=str(get_base_output_dir(series_name) / f"{series_name}_episodes.json"),
            headless=True,
            merge_sources=True,
            scraper_method="crawl4ai",
            parser_mode=series_config.scraping.episodes.parser_mode,
        ),
    )

    characters_metadata = StepBuilder(
        id="scrape_characters",
        phase=SCRAPING,
        module="preprocessor.modules.scraping.character_scraper_step:CharacterScraperStep",
        description="Scrapes character data from wiki",
        produces=["characters.json"],
        needs=[],
        config=CharacterScraperConfig(
            urls=series_config.scraping.characters.urls,
            output_file=str(get_base_output_dir(series_name) / f"{series_name}_characters.json"),
            headless=True,
            scraper_method="crawl4ai",
            parser_mode=series_config.scraping.characters.parser_mode,
        ),
    )

    character_references = StepBuilder(
        id="process_references",
        phase=SCRAPING,
        module="preprocessor.modules.scraping.reference_processor_step:CharacterReferenceStep",
        description="Downloads and processes character reference images",
        produces=["character_faces/{character}/*.jpg"],
        needs=[characters_metadata],
        config=CharacterReferenceConfig(
            characters_file=str(get_base_output_dir(series_name) / f"{series_name}_characters.json"),
            output_dir=str(get_base_output_dir(series_name) / "character_faces"),
            search_engine=series_config.scraping.character_references.search_engine,
            images_per_character=series_config.scraping.character_references.images_per_character,
        ),
    )

    transcoded_videos = StepBuilder(
        id="transcode",
        phase=PROCESSING,
        module="preprocessor.modules.video.transcoding:VideoTranscoderStep",
        description=f"Konwersja do {series_config.processing.transcode.codec} {series_config.processing.transcode.resolution} z adaptacyjnym bitrate",
        produces=["transcoded_videos/{season}/{episode}.mp4"],
        needs=[],
        config=TranscodeConfig(
            video_bitrate_mbps=series_config.processing.transcode.video_bitrate_mbps,
            minrate_mbps=series_config.processing.transcode.minrate_mbps,
            maxrate_mbps=series_config.processing.transcode.maxrate_mbps,
            bufsize_mbps=series_config.processing.transcode.bufsize_mbps,
            gop_size=series_config.processing.transcode.gop_size,
        ),
    )

    scene_data = StepBuilder(
        id="detect_scenes",
        phase=PROCESSING,
        module="preprocessor.modules.video.scene_detection:SceneDetectorStep",
        description="Wykrywa zmiany scen używając TransNetV2",
        produces=["scene_detections/{season}/{episode}.json"],
        needs=[transcoded_videos],
        config=SceneDetectionConfig(
            threshold=series_config.processing.scene_detection.threshold,
            min_scene_len=series_config.processing.scene_detection.min_scene_len,
        ),
    )

    exported_frames = StepBuilder(
        id="export_frames",
        phase=PROCESSING,
        module="preprocessor.modules.video.frame_export:FrameExporterStep",
        description="Eksportuje klatki (PNG) na granicach scen",
        produces=["frames/{season}/{episode}/*.png"],
        needs=[scene_data],
        config=FrameExportConfig(frames_per_scene=series_config.processing.frame_export.frames_per_scene),
    )

    transcription_data = StepBuilder(
        id="transcribe",
        phase=PROCESSING,
        module="preprocessor.modules.text.transcription:TranscriptionStep",
        description=f"Transkrypcja audio używając {series_config.processing.transcription.mode}",
        produces=["transcriptions/{season}/{episode}.json"],
        needs=[transcoded_videos],
        config=WhisperTranscriptionConfig(
            model=series_config.processing.transcription.model,
            language=series_config.processing.transcription.language,
            device=series_config.processing.transcription.device,
            beam_size=10,
            temperature=0.0,
        ),
    )

    separated_audio = StepBuilder(
        id="separate_sounds",
        phase=PROCESSING,
        module="preprocessor.modules.audio.separation:SoundSeparationStep",
        description="Rozdziela dialogi od efektów dźwiękowych",
        produces=["separated_audio/{season}/{episode}/"],
        needs=[transcription_data],
        config=SoundSeparationConfig(),
    )

    text_stats = StepBuilder(
        id="analyze_text",
        phase=PROCESSING,
        module="preprocessor.modules.text.analysis:TextAnalysisStep",
        description="Analiza statystyk tekstu (częstotliwość słów, sentiment)",
        produces=["text_analysis/{season}/{episode}.json"],
        needs=[transcription_data],
        config=TextAnalysisConfig(language=series_config.processing.transcription.language),
    )

    text_embeddings = StepBuilder(
        id="text_embeddings",
        phase=PROCESSING,
        module="preprocessor.modules.text.embeddings:TextEmbeddingStep",
        description="Generuje embeddingi tekstowe używając Qwen2-VL",
        produces=["embeddings/text/{season}/{episode}.npy"],
        needs=[text_stats],
        config=TextEmbeddingConfig(
            model_name="Qwen/Qwen2-VL-8B-Instruct",
            batch_size=8,
            device="cuda",
            text_sentences_per_chunk=5,
            text_chunk_overlap=1,
        ),
    )

    image_hashes = StepBuilder(
        id="image_hashing",
        phase=PROCESSING,
        module="preprocessor.modules.vision.image_hashing:ImageHashStep",
        description="Perceptual hashing klatek (phash, dhash, wavelet)",
        produces=["hashes/{season}/{episode}.json"],
        needs=[exported_frames],
        config=ImageHashConfig(batch_size=32),
    )

    video_embeddings = StepBuilder(
        id="video_embeddings",
        phase=PROCESSING,
        module="preprocessor.modules.vision.embeddings:VideoEmbeddingStep",
        description="Embeddingi wizualne używając Qwen2-VL",
        produces=["embeddings/vision/{season}/{episode}.npy"],
        needs=[exported_frames, image_hashes],
        config=VideoEmbeddingConfig(
            model_name="Qwen/Qwen2-VL-8B-Instruct",
            batch_size=8,
            device="cuda",
        ),
    )

    character_detections = StepBuilder(
        id="detect_characters",
        phase=PROCESSING,
        module="preprocessor.modules.vision.character_detection:CharacterDetectorStep",
        description="Rozpoznaje postacie na klatkach używając InsightFace",
        produces=["detections/characters/{season}/{episode}.json"],
        needs=[exported_frames],
        config=CharacterDetectionConfig(threshold=0.7),
    )

    emotion_data = StepBuilder(
        id="detect_emotions",
        phase=PROCESSING,
        module="preprocessor.modules.vision.emotion_detection:EmotionDetectionStep",
        description="Detekcja emocji na twarzach używając EmoNet",
        produces=["detections/emotions/{season}/{episode}.json"],
        needs=[exported_frames],
        config=EmotionDetectionConfig(),
    )

    face_clusters = StepBuilder(
        id="cluster_faces",
        phase=PROCESSING,
        module="preprocessor.modules.vision.face_clustering:FaceClusteringStep",
        description="Klasteryzacja twarzy używając HDBSCAN",
        produces=["clusters/faces/{season}/{episode}.json"],
        needs=[exported_frames],
        config=FaceClusteringConfig(),
    )

    object_detections = StepBuilder(
        id="detect_objects",
        phase=PROCESSING,
        module="preprocessor.modules.vision.object_detection:ObjectDetectionStep",
        description="Detekcja obiektów ogólnych używając D-FINE",
        produces=["detections/objects/{season}/{episode}.json"],
        needs=[exported_frames],
        config=ObjectDetectionConfig(),
    )

    elastic_documents = StepBuilder(
        id="generate_elastic_docs",
        phase=INDEXING,
        module="preprocessor.modules.search.document_generation:DocumentGeneratorStep",
        description="Łączy wszystkie dane w dokumenty Elasticsearch",
        produces=["elastic_documents/{season}/{episode}.ndjson"],
        needs=[
            text_embeddings,
            video_embeddings,
            character_detections,
            emotion_data,
            face_clusters,
            object_detections,
        ],
        config=DocumentGenerationConfig(generate_segments=True),
    )

    episode_archives = StepBuilder(
        id="generate_archives",
        phase=INDEXING,
        module="preprocessor.modules.packaging.archives:ArchiveGenerationStep",
        description="Tworzy archiwa ZIP per odcinek (wszystkie artefakty)",
        produces=["archives/{season}/{episode}.zip"],
        needs=[elastic_documents],
        config=ArchiveConfig(),
    )

    indexed_data = StepBuilder(
        id="index_to_elasticsearch",
        phase=INDEXING,
        module="preprocessor.modules.search.indexing:ElasticsearchIndexerStep",
        description="Wrzuca dokumenty do Elasticsearch",
        produces=["<elasticsearch_index>"],
        needs=[elastic_documents],
        config=ElasticsearchConfig(
            index_name=series_config.indexing.elasticsearch.index_name,
            host=series_config.indexing.elasticsearch.host,
            dry_run=series_config.indexing.elasticsearch.dry_run,
            append=series_config.indexing.elasticsearch.append,
        ),
    )

    pipeline = Pipeline(name=f"{series_name}_processing")

    pipeline.register(episodes_metadata)
    pipeline.register(characters_metadata)
    pipeline.register(character_references)

    pipeline.register(transcoded_videos)
    pipeline.register(scene_data)
    pipeline.register(exported_frames)

    pipeline.register(transcription_data)
    pipeline.register(separated_audio)
    pipeline.register(text_stats)

    pipeline.register(text_embeddings)
    pipeline.register(image_hashes)
    pipeline.register(video_embeddings)

    pipeline.register(character_detections)
    pipeline.register(emotion_data)
    pipeline.register(face_clusters)
    pipeline.register(object_detections)

    pipeline.register(elastic_documents)
    pipeline.register(episode_archives)
    pipeline.register(indexed_data)

    pipeline.validate()

    return pipeline


def visualize(series_name: str = "ranczo") -> None:
    pipeline = build_pipeline(series_name)
    print(pipeline.to_ascii_art())


def get_step_configs(series_name: str) -> Dict[str, object]:
    pipeline = build_pipeline(series_name)
    return {step_id: step.config for step_id, step in pipeline._steps.items()}
