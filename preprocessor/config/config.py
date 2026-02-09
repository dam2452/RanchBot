from dataclasses import (
    dataclass,
    field,
)
import os
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from pydantic import SecretStr

from preprocessor.utils.resolution import Resolution

# ============================================================================
# CONSTANTS & HELPERS
# ============================================================================

is_docker = os.getenv("DOCKER_CONTAINER", "false").lower() == "true"
BASE_OUTPUT_DIR = Path("/app/output_data") if is_docker else Path("preprocessor/output_data")


def get_base_output_dir(series_name: Optional[str] = None) -> Path:
    base = Path("/app/output_data") if is_docker else Path("preprocessor/output_data")
    if series_name:
        return base / series_name.lower()
    return base


def get_output_path(relative_path: str, series_name: Optional[str] = None) -> Path:
    return get_base_output_dir(series_name) / relative_path


# ============================================================================
# OUTPUT DIRECTORY STRUCTURE
# ============================================================================

@dataclass
class ElasticDocumentSubdirs:
    text_segments: str = "text_segments"
    text_embeddings: str = "text_embeddings"
    video_frames: str = "video_frames"
    episode_names: str = "episode_names"
    text_statistics: str = "text_statistics"
    full_episode_embeddings: str = "full_episode_embeddings"
    sound_events: str = "sound_events"
    sound_event_embeddings: str = "sound_event_embeddings"


@dataclass
class TranscriptionSubdirs:
    raw: str = "raw"
    clean: str = "clean"
    sound_events: str = "sound_events"


@dataclass
class OutputSubdirs:  # pylint: disable=too-many-instance-attributes
    video: str = "transcoded_videos"
    transcriptions: str = "transcriptions"
    transcription_subdirs: TranscriptionSubdirs = field(default_factory=TranscriptionSubdirs)
    scenes: str = "scene_timestamps"
    frames: str = "exported_frames"
    embeddings: str = "embeddings"
    image_hashes: str = "image_hashes"
    character_detections: str = "character_detections"
    character_visualizations: str = "character_detections/visualizations"
    face_clusters: str = "face_clusters"
    object_detections: str = "object_detections"
    object_visualizations: str = "object_detections/visualizations"
    elastic_documents: str = "elastic_documents"
    archives: str = "archives"
    validation_reports: str = "validation_reports"
    elastic_document_subdirs: ElasticDocumentSubdirs = field(default_factory=ElasticDocumentSubdirs)


# ============================================================================
# BASE CLASSES
# ============================================================================

@dataclass
class BaseAPISettings:
    _api_key: Optional[SecretStr] = None

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key.get_secret_value() if self._api_key else None


# ============================================================================
# VIDEO PROCESSING
# ============================================================================

@dataclass
class TranscodeSettings:
    codec: str = "h264_nvenc"
    target_file_size_mb: float = 50.0
    target_duration_seconds: float = 100.0
    audio_bitrate_kbps: int = 128
    gop_size: float = 0.5

    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "transcoded_videos"

    def calculate_video_bitrate_mbps(self) -> float:
        total_bitrate_mbps = (self.target_file_size_mb * 8) / self.target_duration_seconds
        audio_bitrate_mbps = self.audio_bitrate_kbps / 1000.0
        video_bitrate_mbps = total_bitrate_mbps - audio_bitrate_mbps
        return round(video_bitrate_mbps, 2)

    def calculate_minrate_mbps(self, percent: float = 0.5) -> float:
        return round(self.calculate_video_bitrate_mbps() * percent, 2)

    def calculate_maxrate_mbps(self, percent: float = 1.75) -> float:
        return round(self.calculate_video_bitrate_mbps() * percent, 2)

    def calculate_bufsize_mbps(self, multiplier: float = 2.0) -> float:
        return round(self.calculate_video_bitrate_mbps() * multiplier, 2)


@dataclass
class SceneDetectionSettings:
    threshold: float = 0.5
    min_scene_len: int = 10

    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "scene_timestamps"


@dataclass
class SceneChangesSettings:
    frames_per_scene: int = 1


@dataclass
class KeyframeExtractionSettings:
    strategy: str = "scene_changes"
    scene_changes: SceneChangesSettings = field(default_factory=SceneChangesSettings)


@dataclass
class FrameExportSettings:
    resolution: Resolution = Resolution.R1080P

    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "exported_frames"


# ============================================================================
# TRANSCRIPTION & TEXT PROCESSING
# ============================================================================

@dataclass
class TranscriptionSettings:
    model: str = "large-v3-turbo"
    language: str = "Polish"
    device: str = "cuda"

    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "transcriptions"


@dataclass
class WhisperSettings:
    model: str = "large-v3-turbo"

    @classmethod
    def _from_env(cls) -> "WhisperSettings":
        return cls(
            model=os.getenv("WHISPER_MODEL", "large-v3-turbo"),
        )


@dataclass
class TextChunkingSettings:
    segments_per_embedding: int = 5
    text_sentences_per_chunk: int = 8
    text_chunk_overlap: int = 3


@dataclass
class ElevenLabsSettings(BaseAPISettings):
    model_id: str = "scribe_v1"
    language_code: str = "pol"
    diarize: bool = True
    polling_interval: int = 20
    max_attempts: int = 60

    @classmethod
    def _from_env(cls) -> "ElevenLabsSettings":
        api_key = None
        if os.getenv("ELEVEN_API_KEY"):
            api_key = SecretStr(os.getenv("ELEVEN_API_KEY", ""))
        return cls(_api_key=api_key)


# ============================================================================
# EMBEDDINGS
# ============================================================================

@dataclass
class EmbeddingModelSettings:
    model_name: str = "Qwen/Qwen3-VL-Embedding-8B"
    model_revision: str = "main"
    embedding_dim: int = 4096
    gpu_memory_utilization: float = 0.85
    tensor_parallel_size: int = 1
    max_model_len: int = 8192
    image_placeholder: str = "<|vision_start|><|image_pad|><|vision_end|>"
    enable_chunked_prefill: bool = True
    max_num_batched_tokens: int = 8192
    enforce_eager: bool = False


@dataclass
class EmbeddingSettings:
    batch_size: int = 32
    text_batch_size: int = 64
    progress_sub_batch_size: int = 100
    prefetch_chunks: int = 2
    generate_full_episode_embedding: bool = True

    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "embeddings"


# ============================================================================
# COMPUTER VISION
# ============================================================================

@dataclass
class FaceRecognitionSettings:
    model_name: str = "buffalo_l"
    detection_size: Tuple[int, int] = (1280, 1280)


@dataclass
class FaceClusteringSettings:
    min_cluster_size: int = 5
    min_samples: int = 3
    save_noise: bool = True

    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "face_clusters"


@dataclass
class EmotionDetectionSettings:
    model_name: str = "enet_b2_8"

    @classmethod
    def _from_env(cls) -> "EmotionDetectionSettings":
        model_name = os.getenv("EMOTION_MODEL_NAME", "enet_b2_8")
        return cls(model_name=model_name)


@dataclass
class CharacterSettings:
    reference_images_per_character: int = 3
    normalized_face_size: Tuple[int, int] = (112, 112)
    face_detection_threshold: float = 0.2
    reference_matching_threshold: float = 0.50
    frame_detection_threshold: float = 0.55

    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "characters"

    @staticmethod
    def get_characters_list_file(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "characters.json"

    @staticmethod
    def get_detections_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "character_detections"

    @staticmethod
    def get_processed_references_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "character_references_processed"


@dataclass
class ObjectDetectionSettings:
    model_name: str = "ustc-community/dfine-xlarge-obj2coco"
    conf_threshold: float = 0.30

    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "object_detections"

    @staticmethod
    def get_visualized_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "object_detections" / "visualizations"


# ============================================================================
# UTILITIES
# ============================================================================

@dataclass
class ImageHashSettings:
    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "image_hashes"


@dataclass
class ImageScraperSettings(BaseAPISettings):
    max_results_to_scrape: int = 50
    min_image_width: int = 800
    min_image_height: int = 600
    retry_attempts: int = 3
    retry_delay: float = 3.0
    request_delay_min: float = 3.0
    request_delay_max: float = 6.0
    page_navigation_timeout: int = 30000

    @classmethod
    def _from_env(cls) -> "ImageScraperSettings":
        api_key = None
        if os.getenv("SERPAPI_API_KEY"):
            api_key = SecretStr(os.getenv("SERPAPI_API_KEY", ""))
        return cls(_api_key=api_key)

    @property
    def serpapi_key(self) -> Optional[str]:
        return self.api_key


@dataclass
class ScraperSettings:
    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "scraped_pages"


# ============================================================================
# EXTERNAL SERVICES
# ============================================================================

@dataclass
class ElasticsearchSettings:
    host: str = ""
    user: str = ""
    password: str = ""

    @classmethod
    def _from_env(cls) -> "ElasticsearchSettings":
        return cls(
            host=os.getenv("ES_HOST", ""),
            user=os.getenv("ES_USER", ""),
            password=os.getenv("ES_PASS", ""),
        )


@dataclass
class GeminiSettings(BaseAPISettings):
    @classmethod
    def _from_env(cls) -> "GeminiSettings":
        api_key = None
        if os.getenv("GEMINI_API_KEY"):
            api_key = SecretStr(os.getenv("GEMINI_API_KEY", ""))
        return cls(_api_key=api_key)


# ============================================================================
# MAIN SETTINGS
# ============================================================================

@dataclass
class Settings:  # pylint: disable=too-many-instance-attributes
    output_subdirs: OutputSubdirs
    whisper: WhisperSettings
    text_chunking: TextChunkingSettings
    embedding_model: EmbeddingModelSettings
    embedding: EmbeddingSettings
    scene_detection: SceneDetectionSettings
    keyframe_extraction: KeyframeExtractionSettings
    frame_export: FrameExportSettings
    image_hash: ImageHashSettings
    scraper: ScraperSettings
    character: CharacterSettings
    object_detection: ObjectDetectionSettings
    face_recognition: FaceRecognitionSettings
    face_clustering: FaceClusteringSettings
    emotion_detection: EmotionDetectionSettings
    image_scraper: ImageScraperSettings
    elevenlabs: ElevenLabsSettings
    elasticsearch: ElasticsearchSettings
    gemini: GeminiSettings
    transcode: TranscodeSettings
    transcription: TranscriptionSettings

    @classmethod
    def _from_env(cls) -> "Settings":
        return cls(
            output_subdirs=OutputSubdirs(),
            whisper=WhisperSettings._from_env(),
            text_chunking=TextChunkingSettings(),
            embedding_model=EmbeddingModelSettings(),
            embedding=EmbeddingSettings(),
            scene_detection=SceneDetectionSettings(),
            keyframe_extraction=KeyframeExtractionSettings(),
            frame_export=FrameExportSettings(),
            image_hash=ImageHashSettings(),
            scraper=ScraperSettings(),
            character=CharacterSettings(),
            object_detection=ObjectDetectionSettings(),
            face_recognition=FaceRecognitionSettings(),
            face_clustering=FaceClusteringSettings(),
            emotion_detection=EmotionDetectionSettings._from_env(),
            image_scraper=ImageScraperSettings._from_env(),
            elevenlabs=ElevenLabsSettings._from_env(),
            elasticsearch=ElasticsearchSettings._from_env(),
            gemini=GeminiSettings._from_env(),
            transcode=TranscodeSettings(),
            transcription=TranscriptionSettings(),
        )


# ============================================================================
# PIPELINE CONFIGS
# ============================================================================

@dataclass
class TranscodeConfig:
    videos: Path
    transcoded_videos: Path
    resolution: Resolution
    codec: str
    gop_size: float
    episodes_info_json: Optional[Path] = None
    video_bitrate_mbps: Optional[float] = None
    minrate_mbps: Optional[float] = None
    maxrate_mbps: Optional[float] = None
    bufsize_mbps: Optional[float] = None
    audio_bitrate_kbps: int = 128

    def to_dict(self) -> Dict[str, Any]:
        return {
            "videos": self.videos,
            "transcoded_videos": self.transcoded_videos,
            "resolution": self.resolution,
            "codec": self.codec,
            "video_bitrate_mbps": self.video_bitrate_mbps,
            "minrate_mbps": self.minrate_mbps,
            "maxrate_mbps": self.maxrate_mbps,
            "bufsize_mbps": self.bufsize_mbps,
            "audio_bitrate_kbps": self.audio_bitrate_kbps,
            "gop_size": self.gop_size,
            "episodes_info_json": self.episodes_info_json,
        }


@dataclass
class TranscriptionConfig:
    videos: Path
    episodes_info_json: Path
    transcription_jsons: Path
    model: str
    language: str
    device: str
    name: str
    extra_json_keys_to_remove: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "videos": self.videos,
            "episodes_info_json": self.episodes_info_json,
            "transcription_jsons": self.transcription_jsons,
            "model": self.model,
            "language": self.language,
            "device": self.device,
            "extra_json_keys_to_remove": self.extra_json_keys_to_remove,
            "name": self.name,
        }


@dataclass
class IndexConfig:
    name: str
    transcription_jsons: Path
    dry_run: bool = False
    append: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "transcription_jsons": str(self.transcription_jsons),
            "dry_run": self.dry_run,
            "append": self.append,
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

settings = Settings._from_env()
