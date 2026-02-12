from typing import Dict

from preprocessor.app.pipeline import PipelineDefinition
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
    ValidationConfig,
    VideoEmbeddingConfig,
    WhisperTranscriptionConfig,
)
from preprocessor.services.media.resolution import Resolution

SCRAPING = Phase("SCRAPING", color="blue")
PROCESSING = Phase("PROCESSING", color="green")
INDEXING = Phase("INDEXING", color="yellow")
VALIDATION = Phase("VALIDATION", color="magenta")


def build_pipeline(series_name: str) -> PipelineDefinition:  # pylint: disable=too-many-locals
    series_config: SeriesConfig = SeriesConfig.load(series_name)

    episodes_metadata = StepBuilder(
        id="scrape_episodes",
        phase=SCRAPING,
        module="preprocessor.steps.scraping.episode_scraper_step:EpisodeScraperStep",
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
        module="preprocessor.steps.scraping.character_scraper_step:CharacterScraperStep",
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
        module="preprocessor.steps.scraping.reference_processor_step:CharacterReferenceStep",
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

    resolution_analysis = StepBuilder(
        id="resolution_analysis",
        phase=PROCESSING,
        module="preprocessor.steps.analysis.resolution_analysis_step:ResolutionAnalysisStep",
        description="Analyze source video resolutions and warn if upscaling required",
        produces=[],
        needs=[],
        config=TranscodeConfig(
            video_bitrate_mbps=series_config.processing.transcode.video_bitrate_mbps,
            minrate_mbps=series_config.processing.transcode.minrate_mbps,
            maxrate_mbps=series_config.processing.transcode.maxrate_mbps,
            bufsize_mbps=series_config.processing.transcode.bufsize_mbps,
            gop_size=series_config.processing.transcode.gop_size,
            force_deinterlace=series_config.processing.transcode.force_deinterlace,
            resolution=Resolution.from_string(series_config.processing.transcode.resolution),
        ),
    )

    transcoded_videos = StepBuilder(
        id="transcode",
        phase=PROCESSING,
        module="preprocessor.steps.video.transcoding:VideoTranscoderStep",
        description=f"Conversion to {series_config.processing.transcode.codec} {series_config.processing.transcode.resolution} with adaptive bitrate",
        produces=["transcoded_videos/{season}/{episode}.mp4"],
        needs=[resolution_analysis],
        config=TranscodeConfig(
            video_bitrate_mbps=series_config.processing.transcode.video_bitrate_mbps,
            minrate_mbps=series_config.processing.transcode.minrate_mbps,
            maxrate_mbps=series_config.processing.transcode.maxrate_mbps,
            bufsize_mbps=series_config.processing.transcode.bufsize_mbps,
            gop_size=series_config.processing.transcode.gop_size,
            force_deinterlace=series_config.processing.transcode.force_deinterlace,
        ),
    )

    scene_data = StepBuilder(
        id="detect_scenes",
        phase=PROCESSING,
        module="preprocessor.steps.video.scene_detection:SceneDetectorStep",
        description="Detects scene changes using TransNetV2",
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
        module="preprocessor.steps.video.frame_export:FrameExporterStep",
        description="Exports frames (PNG) at scene boundaries",
        produces=["frames/{season}/{episode}/*.png"],
        needs=[scene_data],
        config=FrameExportConfig(frames_per_scene=series_config.processing.frame_export.frames_per_scene),
    )

    transcription_data = StepBuilder(
        id="transcribe",
        phase=PROCESSING,
        module="preprocessor.steps.text.transcription:TranscriptionStep",
        description=f"Audio transcription using {series_config.processing.transcription.mode}",
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
        module="preprocessor.steps.audio.separation:SoundSeparationStep",
        description="Separates dialogue from sound effects",
        produces=["separated_audio/{season}/{episode}/"],
        needs=[transcription_data],
        config=SoundSeparationConfig(),
    )

    text_stats = StepBuilder(
        id="analyze_text",
        phase=PROCESSING,
        module="preprocessor.steps.text.analysis:TextAnalysisStep",
        description="Analyzes text statistics (word frequency, sentiment)",
        produces=["text_analysis/{season}/{episode}.json"],
        needs=[transcription_data],
        config=TextAnalysisConfig(language=series_config.processing.transcription.language),
    )

    text_embeddings = StepBuilder(
        id="text_embeddings",
        phase=PROCESSING,
        module="preprocessor.steps.text.embeddings:TextEmbeddingStep",
        description="Generates text embeddings using Qwen3-VL-Embedding",
        produces=["embeddings/text/{season}/{episode}.npy"],
        needs=[text_stats],
        config=TextEmbeddingConfig(
            model_name="Qwen/Qwen3-VL-Embedding-8B",
            batch_size=8,
            device="cuda",
            text_sentences_per_chunk=5,
            text_chunk_overlap=1,
        ),
    )

    image_hashes = StepBuilder(
        id="image_hashing",
        phase=PROCESSING,
        module="preprocessor.steps.vision.image_hashing:ImageHashStep",
        description="Perceptual frame hashing (phash, dhash, wavelet)",
        produces=["hashes/{season}/{episode}.json"],
        needs=[exported_frames],
        config=ImageHashConfig(batch_size=32),
    )

    video_embeddings = StepBuilder(
        id="video_embeddings",
        phase=PROCESSING,
        module="preprocessor.steps.vision.embeddings:VideoEmbeddingStep",
        description="Visual embeddings using Qwen3-VL-Embedding",
        produces=["embeddings/vision/{season}/{episode}.npy"],
        needs=[exported_frames, image_hashes],
        config=VideoEmbeddingConfig(
            model_name="Qwen/Qwen3-VL-Embedding-8B",
            batch_size=8,
            device="cuda",
        ),
    )

    character_detections = StepBuilder(
        id="detect_characters",
        phase=PROCESSING,
        module="preprocessor.steps.vision.character_detection:CharacterDetectorStep",
        description="Recognizes characters in frames using InsightFace",
        produces=["detections/characters/{season}/{episode}.json"],
        needs=[exported_frames],
        config=CharacterDetectionConfig(threshold=0.7),
    )

    emotion_data = StepBuilder(
        id="detect_emotions",
        phase=PROCESSING,
        module="preprocessor.steps.vision.emotion_detection:EmotionDetectionStep",
        description="Detects emotions on faces using EmoNet",
        produces=["detections/emotions/{season}/{episode}.json"],
        needs=[exported_frames],
        config=EmotionDetectionConfig(),
    )

    face_clusters = StepBuilder(
        id="cluster_faces",
        phase=PROCESSING,
        module="preprocessor.steps.vision.face_clustering:FaceClusteringStep",
        description="Face clustering using HDBSCAN",
        produces=["clusters/faces/{season}/{episode}.json"],
        needs=[exported_frames],
        config=FaceClusteringConfig(),
    )

    object_detections = StepBuilder(
        id="detect_objects",
        phase=PROCESSING,
        module="preprocessor.steps.vision.object_detection:ObjectDetectionStep",
        description="General object detection using D-FINE",
        produces=["detections/objects/{season}/{episode}.json"],
        needs=[exported_frames],
        config=ObjectDetectionConfig(),
    )

    elastic_documents = StepBuilder(
        id="generate_elastic_docs",
        phase=INDEXING,
        module="preprocessor.steps.search.document_generation:DocumentGeneratorStep",
        description="Combines all data into Elasticsearch documents",
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
        module="preprocessor.steps.packaging.archives:ArchiveGenerationStep",
        description="Creates ZIP archives per episode (all artifacts)",
        produces=["archives/{season}/{episode}.zip"],
        needs=[elastic_documents],
        config=ArchiveConfig(),
    )

    indexed_data = StepBuilder(
        id="index_to_elasticsearch",
        phase=INDEXING,
        module="preprocessor.steps.search.indexing:ElasticsearchIndexerStep",
        description="Indexes documents into Elasticsearch",
        produces=["<elasticsearch_index>"],
        needs=[elastic_documents],
        config=ElasticsearchConfig(
            index_name=series_config.indexing.elasticsearch.index_name,
            host=series_config.indexing.elasticsearch.host,
            dry_run=series_config.indexing.elasticsearch.dry_run,
            append=series_config.indexing.elasticsearch.append,
        ),
    )

    validation = StepBuilder(
        id="validate",
        phase=VALIDATION,
        module="preprocessor.steps.validation.validator_step:ValidationStep",
        description="Validates all processed data and generates reports",
        produces=["validation_reports/{season}/"],
        needs=[indexed_data, episode_archives],
        config=ValidationConfig(),
    )

    pipeline = PipelineDefinition(name=f"{series_name}_processing")

    pipeline.register(episodes_metadata)
    pipeline.register(characters_metadata)
    pipeline.register(character_references)

    pipeline.register(resolution_analysis)
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
    pipeline.register(validation)

    pipeline.validate()

    return pipeline


def visualize(series_name: str = "ranczo") -> None:
    pipeline = build_pipeline(series_name)
    print(pipeline.to_ascii_art())


def __get_step_configs(series_name: str) -> Dict[str, object]:
    pipeline = build_pipeline(series_name)
    return {step_id: step.config for step_id, step in pipeline.get_all_steps().items()}
