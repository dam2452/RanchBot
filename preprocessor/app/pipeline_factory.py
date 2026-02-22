from typing import Dict

from preprocessor.app.pipeline import PipelineDefinition
from preprocessor.app.step_builder import (
    Phase,
    StepBuilder,
)
from preprocessor.config.series_config import SeriesConfig
from preprocessor.config.step_configs import (
    ArchiveConfig,
    CharacterDetectionConfig,
    CharacterReferenceConfig,
    CharacterReferenceProcessorConfig,
    CharacterScraperConfig,
    DocumentGenerationConfig,
    ElasticsearchConfig,
    EmotionDetectionConfig,
    EpisodeNameEmbeddingConfig,
    EpisodeScraperConfig,
    FaceClusteringConfig,
    FrameExportConfig,
    FullEpisodeEmbeddingConfig,
    ImageHashConfig,
    ObjectDetectionConfig,
    ResolutionAnalysisConfig,
    SceneDetectionConfig,
    SoundEventEmbeddingConfig,
    SoundEventsConfig,
    SoundSeparationConfig,
    TextAnalysisConfig,
    TextCleaningConfig,
    TextEmbeddingConfig,
    TranscodeConfig,
    TranscriptionConfig,
    ValidationConfig,
    VideoEmbeddingConfig,
)
from preprocessor.core.output_descriptors import (
    DirectoryOutput,
    FileOutput,
    JsonFileOutput,
    create_frames_output,
)
from preprocessor.services.media.resolution import Resolution
from preprocessor.steps.analysis.resolution_analysis_step import ResolutionAnalysisStep
from preprocessor.steps.audio.separation_step import SoundSeparationStep
from preprocessor.steps.packaging.archives_step import ArchiveGenerationStep
from preprocessor.steps.scraping.character_scraper_step import CharacterScraperStep
from preprocessor.steps.scraping.episode_scraper_step import EpisodeScraperStep
from preprocessor.steps.scraping.reference_processor_step import CharacterReferenceStep
from preprocessor.steps.search.document_generation_step import DocumentGeneratorStep
from preprocessor.steps.search.indexing_step import ElasticsearchIndexerStep
from preprocessor.steps.text.analysis_step import TextAnalysisStep
from preprocessor.steps.text.embeddings_step import TextEmbeddingStep
from preprocessor.steps.text.episode_name_embedding_step import EpisodeNameEmbeddingStep
from preprocessor.steps.text.full_episode_embedding_step import FullEpisodeEmbeddingStep
from preprocessor.steps.text.sound_event_embedding_step import SoundEventEmbeddingStep
from preprocessor.steps.text.sound_events_step import SoundEventsStep
from preprocessor.steps.text.text_cleaning_step import TextCleaningStep
from preprocessor.steps.text.transcription_step import TranscriptionStep
from preprocessor.steps.validation.validator_step import ValidationStep
from preprocessor.steps.video.frame_export_step import FrameExporterStep
from preprocessor.steps.video.scene_detection_step import SceneDetectorStep
from preprocessor.steps.video.transcoding_step import VideoTranscoderStep
from preprocessor.steps.vision.character_detection_step import CharacterDetectorStep
from preprocessor.steps.vision.character_reference_processor_step import CharacterReferenceProcessorStep
from preprocessor.steps.vision.embeddings_step import VideoEmbeddingStep
from preprocessor.steps.vision.emotion_detection_step import EmotionDetectionStep
from preprocessor.steps.vision.face_clustering_step import FaceClusteringStep
from preprocessor.steps.vision.image_hashing_step import ImageHashStep
from preprocessor.steps.vision.object_detection_step import ObjectDetectionStep

# Phase Definitions
SCRAPING = Phase("SCRAPING", color="blue")
PROCESSING = Phase("PROCESSING", color="green")
INDEXING = Phase("INDEXING", color="yellow")
VALIDATION = Phase("VALIDATION", color="magenta")


def build_pipeline(series_name: str) -> PipelineDefinition:  # pylint: disable=too-many-locals,too-many-statements
    series_config = SeriesConfig.load(series_name)

    # =========================================================
    # SCRAPING PHASE
    # =========================================================
    episodes_metadata = StepBuilder(
        phase=SCRAPING,
        step_class=EpisodeScraperStep,
        description="Scrapes episode metadata from wiki",
        produces=[
            JsonFileOutput(
                pattern=f"{series_name}_episodes.json",
                subdir="",
                min_size_bytes=100,
            ),
        ],
        needs=[],
        config=EpisodeScraperConfig(
            urls=series_config.scraping.episodes.urls,
            headless=True,
            merge_sources=True,
            scraper_method="crawl4ai",
            parser_mode=series_config.scraping.episodes.parser_mode,
        ),
    )

    characters_metadata = StepBuilder(
        phase=SCRAPING,
        step_class=CharacterScraperStep,
        description="Scrapes character data from wiki",
        produces=[
            JsonFileOutput(
                pattern=f"{series_name}_characters.json",
                subdir="",
                min_size_bytes=50,
            ),
        ],
        needs=[],
        config=CharacterScraperConfig(
            urls=series_config.scraping.characters.urls,
            headless=True,
            scraper_method="crawl4ai",
            parser_mode=series_config.scraping.characters.parser_mode,
        ),
    )

    character_references = StepBuilder(
        phase=SCRAPING,
        step_class=CharacterReferenceStep,
        description="Downloads character reference images from the web",
        produces=[
            DirectoryOutput(
                pattern="character_faces",
                subdir="",
                expected_file_pattern="**/*.jpg",
                min_files=1,
                min_size_per_file_bytes=1024,
            ),
        ],
        needs=[characters_metadata],
        config=CharacterReferenceConfig(
            search_engine=series_config.scraping.character_references.search_engine,
            images_per_character=series_config.scraping.character_references.images_per_character,
        ),
    )

    character_reference_vectors = StepBuilder(
        phase=SCRAPING,
        step_class=CharacterReferenceProcessorStep,
        description="Processes character reference images into face embedding vectors",
        produces=[
            DirectoryOutput(
                pattern="character_references_processed",
                subdir="",
                expected_file_pattern="**/face_vector.npy",
                min_files=1,
                min_size_per_file_bytes=100,
            ),
        ],
        needs=[character_references],
        config=CharacterReferenceProcessorConfig(),
    )

    # =========================================================
    # PROCESSING PHASE: VIDEO
    # =========================================================
    resolution_analysis = StepBuilder(
        phase=PROCESSING,
        step_class=ResolutionAnalysisStep,
        description="Analyze source video resolutions and warn if upscaling required",
        produces=[],
        needs=[],
        config=ResolutionAnalysisConfig(
            resolution=Resolution.from_string(series_config.processing.transcode.resolution),
        ),
    )

    transcoded_videos = StepBuilder(
        phase=PROCESSING,
        step_class=VideoTranscoderStep,
        description=f"Conversion to h264_nvenc {series_config.processing.transcode.resolution} with adaptive bitrate",
        produces=[
            FileOutput(
                pattern="{season}/{episode}.mp4",
                min_size_bytes=1024 * 1024,
            ),
        ],
        needs=[resolution_analysis],
        config=TranscodeConfig(
            max_bitrate_file_size_mb=series_config.processing.transcode.max_bitrate_file_size_mb,
            max_bitrate_duration_seconds=series_config.processing.transcode.max_bitrate_duration_seconds,
            keyframe_interval_seconds=series_config.processing.transcode.keyframe_interval_seconds,
            min_bitrate_mbps=series_config.processing.transcode.min_bitrate_mbps,
            bitrate_boost_ratio=series_config.processing.transcode.bitrate_boost_ratio,
            force_deinterlace=series_config.processing.transcode.force_deinterlace,
        ),
    )

    scene_data = StepBuilder(
        phase=PROCESSING,
        step_class=SceneDetectorStep,
        description="Detects scene changes using TransNetV2",
        produces=[
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ],
        needs=[transcoded_videos],
        config=SceneDetectionConfig(
            threshold=series_config.processing.scene_detection.threshold,
            min_scene_len=series_config.processing.scene_detection.min_scene_len,
        ),
    )

    # Frame export output descriptor matches FrameExporterStep.get_output_descriptors()
    # Defined here for pipeline validation before step instantiation
    exported_frames = StepBuilder(
        phase=PROCESSING,
        step_class=FrameExporterStep,
        description="Exports frames (PNG) at scene boundaries",
        produces=[create_frames_output()],
        needs=[scene_data],
        config=FrameExportConfig(
            frames_per_scene=series_config.processing.frame_export.frames_per_scene,
        ),
    )

    # =========================================================
    # PROCESSING PHASE: TEXT & AUDIO
    # =========================================================
    transcription_data = StepBuilder(
        phase=PROCESSING,
        step_class=TranscriptionStep,
        description=f"Audio transcription using {series_config.processing.transcription.mode}",
        produces=[
            JsonFileOutput(
                pattern="{season}/{episode}/{episode}.json",
                min_size_bytes=50,
            ),
        ],
        needs=[transcoded_videos],
        config=TranscriptionConfig(
            mode=series_config.processing.transcription.mode,
            model=series_config.processing.transcription.model,
            language=series_config.processing.transcription.language,
            device=series_config.processing.transcription.device,
        ),
    )

    text_cleaning = StepBuilder(
        phase=PROCESSING,
        step_class=TextCleaningStep,
        description="Removes sound events from transcription segments",
        produces=[
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ],
        needs=[transcription_data],
        config=TextCleaningConfig(),
    )

    sound_events = StepBuilder(
        phase=PROCESSING,
        step_class=SoundEventsStep,
        description="Extracts sound event segments from transcription",
        produces=[
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ],
        needs=[transcription_data],
        config=SoundEventsConfig(),
    )

    separated_audio = StepBuilder(
        phase=PROCESSING,
        step_class=SoundSeparationStep,
        description="Separates dialogue from sound effects",
        produces=[
            DirectoryOutput(
                pattern="{season}/{episode}",
                expected_file_pattern="*.wav",
                min_files=1,
                min_size_per_file_bytes=1024,
            ),
        ],
        needs=[transcription_data],
        config=SoundSeparationConfig(),
    )

    text_stats = StepBuilder(
        phase=PROCESSING,
        step_class=TextAnalysisStep,
        description="Analyzes text statistics (word frequency, sentiment)",
        produces=[
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=50,
            ),
        ],
        needs=[text_cleaning],
        config=TextAnalysisConfig(language=series_config.processing.transcription.language),
    )

    text_embeddings = StepBuilder(
        phase=PROCESSING,
        step_class=TextEmbeddingStep,
        description="Generates text embeddings using Qwen3-VL-Embedding",
        produces=[
            FileOutput(
                pattern="{season}/{episode}.npy",
                min_size_bytes=1024,
            ),
        ],
        needs=[text_stats],
        config=TextEmbeddingConfig(
            model_name="Qwen/Qwen3-VL-Embedding-8B",
            batch_size=8,
            device="cuda",
            text_sentences_per_chunk=8,
            text_chunk_overlap=3,
        ),
    )

    sound_event_embeddings = StepBuilder(
        phase=PROCESSING,
        step_class=SoundEventEmbeddingStep,
        description="Generates sound event embeddings using Qwen3-VL-Embedding",
        produces=[
            FileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=1024,
            ),
        ],
        needs=[sound_events],
        config=SoundEventEmbeddingConfig(
            model_name="Qwen/Qwen3-VL-Embedding-8B",
            batch_size=64,
            device="cuda",
        ),
    )

    full_episode_embeddings = StepBuilder(
        phase=PROCESSING,
        step_class=FullEpisodeEmbeddingStep,
        description="Generates full episode embedding using Qwen3-VL-Embedding",
        produces=[
            FileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=1024,
            ),
        ],
        needs=[text_cleaning],
        config=FullEpisodeEmbeddingConfig(
            model_name="Qwen/Qwen3-VL-Embedding-8B",
            device="cuda",
        ),
    )

    episode_name_embeddings = StepBuilder(
        phase=PROCESSING,
        step_class=EpisodeNameEmbeddingStep,
        description="Generates episode title embedding using Qwen3-VL-Embedding",
        produces=[
            FileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=1024,
            ),
        ],
        needs=[text_cleaning],
        config=EpisodeNameEmbeddingConfig(
            model_name="Qwen/Qwen3-VL-Embedding-8B",
            device="cuda",
        ),
    )

    # =========================================================
    # PROCESSING PHASE: VISION
    # =========================================================
    image_hashes = StepBuilder(
        phase=PROCESSING,
        step_class=ImageHashStep,
        description="Perceptual frame hashing (phash, dhash, wavelet)",
        produces=[
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=50,
            ),
        ],
        needs=[exported_frames],
        config=ImageHashConfig(batch_size=32),
    )

    video_embeddings = StepBuilder(
        phase=PROCESSING,
        step_class=VideoEmbeddingStep,
        description="Visual embeddings using Qwen3-VL-Embedding",
        produces=[
            FileOutput(
                pattern="{season}/{episode}.npy",
                min_size_bytes=1024,
            ),
        ],
        needs=[exported_frames, image_hashes],
        config=VideoEmbeddingConfig(
            model_name="Qwen/Qwen3-VL-Embedding-8B",
            batch_size=8,
            device="cuda",
        ),
    )

    character_detections = StepBuilder(
        phase=PROCESSING,
        step_class=CharacterDetectorStep,
        description="Recognizes characters in frames using InsightFace",
        produces=[
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ],
        needs=[exported_frames, character_reference_vectors],
        config=CharacterDetectionConfig(threshold=0.45, max_parallel_episodes=4),
    )

    emotion_data = StepBuilder(
        phase=PROCESSING,
        step_class=EmotionDetectionStep,
        description="Detects emotions on faces using EmoNet",
        produces=[
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ],
        needs=[exported_frames],
        config=EmotionDetectionConfig(),
    )

    face_clusters = StepBuilder(
        phase=PROCESSING,
        step_class=FaceClusteringStep,
        description="Face clustering using HDBSCAN",
        produces=[
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ],
        needs=[exported_frames],
        config=FaceClusteringConfig(),
    )

    object_detections = StepBuilder(
        phase=PROCESSING,
        step_class=ObjectDetectionStep,
        description="General object detection using D-FINE",
        produces=[
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                min_size_bytes=10,
            ),
        ],
        needs=[exported_frames],
        config=ObjectDetectionConfig(),
    )

    # =========================================================
    # INDEXING PHASE
    # =========================================================
    elastic_documents = StepBuilder(
        phase=INDEXING,
        step_class=DocumentGeneratorStep,
        description="Combines all data into Elasticsearch documents",
        produces=[
            FileOutput(
                pattern="{season}/{episode}.ndjson",
                min_size_bytes=100,
            ),
        ],
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
        phase=INDEXING,
        step_class=ArchiveGenerationStep,
        description="Creates ZIP archives per episode (all artifacts)",
        produces=[
            FileOutput(
                pattern="{season}/{episode}.zip",
                min_size_bytes=1024 * 100,
            ),
        ],
        needs=[elastic_documents],
        config=ArchiveConfig(),
    )

    indexed_data = StepBuilder(
        phase=INDEXING,
        step_class=ElasticsearchIndexerStep,
        description="Indexes documents into Elasticsearch",
        produces=[],
        needs=[elastic_documents],
        config=ElasticsearchConfig(
            index_name=series_config.indexing.elasticsearch.index_name,
            host=series_config.indexing.elasticsearch.host,
            dry_run=series_config.indexing.elasticsearch.dry_run,
            append=series_config.indexing.elasticsearch.append,
        ),
    )

    # =========================================================
    # VALIDATION PHASE
    # =========================================================
    validation = StepBuilder(
        phase=VALIDATION,
        step_class=ValidationStep,
        description="Validates all processed data and generates reports",
        produces=[
            DirectoryOutput(
                pattern="{season}",
                expected_file_pattern="*.json",
                min_files=1,
                min_size_per_file_bytes=50,
            ),
        ],
        needs=[indexed_data, episode_archives],
        config=ValidationConfig(),
    )

    # =========================================================
    # PIPELINE REGISTRATION
    # =========================================================
    pipeline = PipelineDefinition(name=f"{series_name}_processing")

    pipeline.register(episodes_metadata)
    pipeline.register(characters_metadata)
    pipeline.register(character_references)
    pipeline.register(character_reference_vectors)

    pipeline.register(resolution_analysis)
    pipeline.register(transcoded_videos)
    pipeline.register(scene_data)
    pipeline.register(exported_frames)

    pipeline.register(transcription_data)
    pipeline.register(text_cleaning)
    pipeline.register(sound_events)
    pipeline.register(separated_audio)
    pipeline.register(text_stats)

    pipeline.register(text_embeddings)
    pipeline.register(sound_event_embeddings)
    pipeline.register(full_episode_embeddings)
    pipeline.register(episode_name_embeddings)
    pipeline.register(image_hashes)
    pipeline.register(video_embeddings)

    pipeline.register(object_detections)
    pipeline.register(character_detections)
    pipeline.register(emotion_data)
    pipeline.register(face_clusters)

    pipeline.register(elastic_documents)
    pipeline.register(episode_archives)
    pipeline.register(indexed_data)
    pipeline.register(validation)

    pipeline.validate()

    return pipeline


def visualize(series_name: str = "ranczo") -> None:
    pipeline = build_pipeline(series_name)
    print(pipeline.to_ascii_art())


def _get_step_configs(series_name: str) -> Dict[str, object]:
    pipeline = build_pipeline(series_name)
    return {step_id: step.config for step_id, step in pipeline.get_all_steps().items()}
