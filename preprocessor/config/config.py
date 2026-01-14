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
)

from pydantic import SecretStr

from preprocessor.utils.resolution import Resolution

is_docker = os.getenv("DOCKER_CONTAINER", "false").lower() == "true"
BASE_OUTPUT_DIR = Path("/app/output_data") if is_docker else Path("preprocessor/output_data")


def get_output_path(relative_path: str) -> Path:
    return BASE_OUTPUT_DIR / relative_path


@dataclass
class OutputSubdirs:
    video: str = "transcoded_videos"
    transcriptions: str = "transcriptions"
    scenes: str = "scene_timestamps"
    frames: str = "exported_frames"
    embeddings: str = "embeddings"
    image_hashes: str = "image_hashes"
    character_detections: str = "character_detections"
    object_detections: str = "object_detections"
    object_visualizations: str = "object_detections/visualizations"
    elastic_documents: str = "elastic_documents"


@dataclass
class WhisperSettings:
    model: str = "large-v3-turbo"

    @classmethod
    def from_env(cls) -> "WhisperSettings":
        return cls(
            model=os.getenv("WHISPER_MODEL", "large-v3-turbo"),
        )

@dataclass
class TextChunkingSettings:
    segments_per_embedding: int = 5
    use_sentence_based_chunking: bool = True
    text_sentences_per_chunk: int = 8
    text_chunk_overlap: int = 3

@dataclass
class EmbeddingModelSettings:
    model_name: str = "Qwen/Qwen3-VL-Embedding-8B"
    model_revision: str = "main"
    gpu_memory_utilization: float = 0.85
    tensor_parallel_size: int = 1
    max_model_len: int = 8192
    image_placeholder: str = "<|vision_start|><|image_pad|><|vision_end|>"
    enable_chunked_prefill: bool = True
    max_num_batched_tokens: int = 8192
    enforce_eager: bool = True

@dataclass
class EmbeddingSettings:
    default_output_dir: Path = BASE_OUTPUT_DIR / "embeddings"
    batch_size: int = 32
    progress_sub_batch_size: int = 100
    prefetch_chunks: int = 2

@dataclass
class SceneDetectionSettings:
    threshold: float = 0.5
    min_scene_len: int = 10
    output_dir: Path = BASE_OUTPUT_DIR / "scene_timestamps"

@dataclass
class KeyframeExtractionSettings:
    strategy: str = "scene_changes"
    interval: int = 1
    frames_per_scene: int = 1
    color_diff_threshold: float = 0.3
    scene_fps_default: float = 30.0
    interval_multiplier: int = 5

@dataclass
class FrameExportSettings:
    output_dir: Path = BASE_OUTPUT_DIR / "exported_frames"
    frame_height: int = 1080

@dataclass
class ImageHashSettings:
    output_dir: Path = BASE_OUTPUT_DIR / "image_hashes"

@dataclass
class ScraperSettings:
    output_dir: Path = BASE_OUTPUT_DIR / "scraped_pages"

@dataclass
class CharacterSettings:
    output_dir: Path = BASE_OUTPUT_DIR / "characters"
    reference_images_per_character: int = 3
    characters_list_file: Path = BASE_OUTPUT_DIR / "characters.json"
    detections_dir: Path = BASE_OUTPUT_DIR / "character_detections"

@dataclass
class ObjectDetectionSettings:
    model_name: str = "ustc-community/dfine-xlarge-obj2coco"
    conf_threshold: float = 0.30
    output_dir: Path = BASE_OUTPUT_DIR / "object_detections"
    visualized_output_dir: Path = BASE_OUTPUT_DIR / "object_detections" / "visualizations"

@dataclass
class FaceRecognitionSettings:
    model_name: str = "buffalo_l"
    detection_size: tuple = (640, 640)
    threshold: float = 0.55
    use_gpu: bool = True

@dataclass
class ImageScraperSettings:
    max_results_to_scrape: int = 50
    min_image_width: int = 800
    min_image_height: int = 600
    retry_attempts: int = 3
    retry_delay: float = 3.0
    request_delay_min: float = 3.0
    request_delay_max: float = 6.0
    page_navigation_timeout: int = 30000
    _serpapi_key: Optional[SecretStr] = None

    @classmethod
    def from_env(cls) -> "ImageScraperSettings":
        api_key = None
        if os.getenv("SERPAPI_API_KEY"):
            api_key = SecretStr(os.getenv("SERPAPI_API_KEY", ""))
        return cls(_serpapi_key=api_key)

    @property
    def serpapi_key(self) -> Optional[str]:
        return self._serpapi_key.get_secret_value() if self._serpapi_key else None

@dataclass
class ElevenLabsSettings:
    model_id: str = "scribe_v1"
    language_code: str = "pol"
    diarize: bool = True
    diarization_threshold: float = 0.4
    temperature: float = 0.0
    polling_interval: int = 20
    max_attempts: int = 60
    _api_key: Optional[SecretStr] = None

    @classmethod
    def from_env(cls) -> "ElevenLabsSettings":
        api_key = None
        if os.getenv("ELEVEN_API_KEY"):
            api_key = SecretStr(os.getenv("ELEVEN_API_KEY", ""))
        return cls(_api_key=api_key)

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key.get_secret_value() if self._api_key else None

@dataclass
class ElasticsearchSettings:
    host: str = ""
    user: str = ""
    password: str = ""

    @classmethod
    def from_env(cls) -> "ElasticsearchSettings":
        return cls(
            host=os.getenv("ES_HOST", ""),
            user=os.getenv("ES_USER", ""),
            password=os.getenv("ES_PASS", ""),
        )

@dataclass
class GeminiSettings:
    _api_key: Optional[SecretStr] = None

    @classmethod
    def from_env(cls) -> "GeminiSettings":
        api_key = None
        if os.getenv("GEMINI_API_KEY"):
            api_key = SecretStr(os.getenv("GEMINI_API_KEY", ""))
        return cls(_api_key=api_key)

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key.get_secret_value() if self._api_key else None

@dataclass
class TranscodeDefaults:
    output_dir: Path = BASE_OUTPUT_DIR / "transcoded_videos"
    codec: str = "h264_nvenc"
    preset: str = "slow"
    crf: int = 31
    gop_size: float = 0.5

@dataclass
class TranscriptionDefaults:
    output_dir: Path = BASE_OUTPUT_DIR / "transcriptions"
    model: str = "large-v3-turbo"
    language: str = "Polish"
    device: str = "cuda"

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
    image_scraper: ImageScraperSettings
    elevenlabs: ElevenLabsSettings
    elasticsearch: ElasticsearchSettings
    gemini: GeminiSettings
    transcode: TranscodeDefaults
    transcription: TranscriptionDefaults

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            output_subdirs=OutputSubdirs(),
            whisper=WhisperSettings.from_env(),
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
            image_scraper=ImageScraperSettings.from_env(),
            elevenlabs=ElevenLabsSettings.from_env(),
            elasticsearch=ElasticsearchSettings.from_env(),
            gemini=GeminiSettings.from_env(),
            transcode=TranscodeDefaults(),
            transcription=TranscriptionDefaults(),
        )

settings = Settings.from_env()

@dataclass
class TranscodeConfig:
    videos: Path
    transcoded_videos: Path
    resolution: Resolution
    codec: str
    preset: str
    crf: int
    gop_size: float
    episodes_info_json: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "videos": self.videos,
            "transcoded_videos": self.transcoded_videos,
            "resolution": self.resolution,
            "codec": self.codec,
            "preset": self.preset,
            "crf": self.crf,
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
