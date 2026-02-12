from dataclasses import (
    dataclass,
    field,
)
import os
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
)

from pydantic import SecretStr

from preprocessor.config.mixins import OutputDirMixin
from preprocessor.services.media.resolution import Resolution


@dataclass
class ElasticDocumentSubdirs:
    episode_names: str = 'episode_names'
    full_episode_embeddings: str = 'full_episode_embeddings'
    sound_event_embeddings: str = 'sound_event_embeddings'
    sound_events: str = 'sound_events'
    text_embeddings: str = 'text_embeddings'
    text_segments: str = 'text_segments'
    text_statistics: str = 'text_statistics'
    video_frames: str = 'video_frames'

@dataclass
class TranscriptionSubdirs:
    clean: str = 'clean'
    raw: str = 'raw'
    sound_events: str = 'sound_events'

@dataclass
class OutputSubdirs:  # pylint: disable=too-many-instance-attributes
    archives: str = 'archives'
    character_detections: str = 'character_detections'
    character_visualizations: str = 'character_detections/visualizations'
    elastic_document_subdirs: ElasticDocumentSubdirs = field(default_factory=ElasticDocumentSubdirs)
    elastic_documents: str = 'elastic_documents'
    embeddings: str = 'embeddings'
    face_clusters: str = 'face_clusters'
    frames: str = 'exported_frames'
    image_hashes: str = 'image_hashes'
    object_detections: str = 'object_detections'
    object_visualizations: str = 'object_detections/visualizations'
    scenes: str = 'scene_timestamps'
    transcription_subdirs: TranscriptionSubdirs = field(default_factory=TranscriptionSubdirs)
    transcriptions: str = 'transcriptions'
    validation_reports: str = 'validation_reports'
    video: str = 'transcoded_videos'

@dataclass
class BaseAPISettings:
    _api_key: Optional[SecretStr] = None

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key.get_secret_value() if self._api_key else None

@dataclass
class TranscodeSettings(OutputDirMixin):
    OUTPUT_SUBDIR: ClassVar[str] = 'transcoded_videos'

    audio_bitrate_kbps: int = 128
    codec: str = 'h264_nvenc'
    gop_size: float = 0.5
    target_duration_seconds: float = 100.0
    target_file_size_mb: float = 50.0

@dataclass
class SceneDetectionSettings(OutputDirMixin):
    OUTPUT_SUBDIR: ClassVar[str] = 'scene_timestamps'

    min_scene_len: int = 10
    threshold: float = 0.5

@dataclass
class SceneChangesSettings:
    frames_per_scene: int = 1

@dataclass
class KeyframeExtractionSettings:
    scene_changes: SceneChangesSettings = field(default_factory=SceneChangesSettings)
    strategy: str = 'scene_changes'

@dataclass
class FrameExportSettings(OutputDirMixin):
    OUTPUT_SUBDIR: ClassVar[str] = 'exported_frames'

    resolution: Resolution = Resolution.R1080P

@dataclass
class TranscriptionSettings(OutputDirMixin):
    OUTPUT_SUBDIR: ClassVar[str] = 'transcriptions'

    device: str = 'cuda'
    language: str = 'Polish'
    model: str = 'large-v3-turbo'

@dataclass
class WhisperSettings:
    model: str = 'large-v3-turbo'

    @classmethod
    def _from_env(cls) -> 'WhisperSettings':
        return cls(model=os.getenv('WHISPER_MODEL', 'large-v3-turbo'))

@dataclass
class TextChunkingSettings:
    segments_per_embedding: int = 5
    text_chunk_overlap: int = 3
    text_sentences_per_chunk: int = 8

@dataclass
class ElevenLabsSettings(BaseAPISettings):
    diarize: bool = True
    language_code: str = 'pol'
    max_attempts: int = 60
    model_id: str = 'scribe_v1'
    polling_interval: int = 20

    @classmethod
    def _from_env(cls) -> 'ElevenLabsSettings':
        api_key = None
        if os.getenv('ELEVEN_API_KEY'):
            api_key = SecretStr(os.getenv('ELEVEN_API_KEY', ''))
        return cls(_api_key=api_key)

@dataclass
class EmbeddingModelSettings:
    embedding_dim: int = 4096
    enable_chunked_prefill: bool = True
    enforce_eager: bool = False
    gpu_memory_utilization: float = 0.85
    image_placeholder: str = '<|vision_start|><|image_pad|><|vision_end|>'
    max_model_len: int = 8192
    max_num_batched_tokens: int = 8192
    model_name: str = 'Qwen/Qwen3-VL-Embedding-8B'
    model_revision: str = 'main'
    tensor_parallel_size: int = 1

@dataclass
class EmbeddingSettings(OutputDirMixin):
    OUTPUT_SUBDIR: ClassVar[str] = 'embeddings'

    batch_size: int = 32
    generate_full_episode_embedding: bool = True
    prefetch_chunks: int = 2
    progress_sub_batch_size: int = 100
    text_batch_size: int = 64

@dataclass
class FaceRecognitionSettings:
    detection_size: Tuple[int, int] = (1280, 1280)
    model_name: str = 'buffalo_l'

@dataclass
class FaceClusteringSettings(OutputDirMixin):
    OUTPUT_SUBDIR: ClassVar[str] = 'face_clusters'

    min_cluster_size: int = 5
    min_samples: int = 3
    save_noise: bool = True

@dataclass
class EmotionDetectionSettings:
    model_name: str = 'enet_b2_8'

    @classmethod
    def _from_env(cls) -> 'EmotionDetectionSettings':
        model_name = os.getenv('EMOTION_MODEL_NAME', 'enet_b2_8')
        return cls(model_name=model_name)

@dataclass
class CharacterSettings(OutputDirMixin):
    OUTPUT_SUBDIR: ClassVar[str] = 'characters'

    face_detection_threshold: float = 0.2
    frame_detection_threshold: float = 0.55
    normalized_face_size: Tuple[int, int] = (112, 112)
    reference_images_per_character: int = 3
    reference_matching_threshold: float = 0.5

@dataclass
class ObjectDetectionSettings(OutputDirMixin):
    OUTPUT_SUBDIR: ClassVar[str] = 'object_detections'

    conf_threshold: float = 0.3
    model_name: str = 'ustc-community/dfine-xlarge-obj2coco'

@dataclass
class ImageHashSettings(OutputDirMixin):
    OUTPUT_SUBDIR: ClassVar[str] = 'image_hashes'

@dataclass
class ImageScraperSettings(BaseAPISettings):
    max_results_to_scrape: int = 50
    min_image_height: int = 600
    min_image_width: int = 800
    page_navigation_timeout: int = 30000
    request_delay_max: float = 6.0
    request_delay_min: float = 3.0
    retry_attempts: int = 3
    retry_delay: float = 3.0

    @property
    def serpapi_key(self) -> Optional[str]:
        return self.api_key

    @classmethod
    def _from_env(cls) -> 'ImageScraperSettings':
        api_key = None
        if os.getenv('SERPAPI_API_KEY'):
            api_key = SecretStr(os.getenv('SERPAPI_API_KEY', ''))
        return cls(_api_key=api_key)

@dataclass
class ScraperSettings(OutputDirMixin):
    OUTPUT_SUBDIR: ClassVar[str] = 'scraped_pages'

@dataclass
class ElasticsearchSettings:
    host: str = ''
    password: str = ''
    user: str = ''

    @classmethod
    def _from_env(cls) -> 'ElasticsearchSettings':
        return cls(host=os.getenv('ES_HOST', ''), user=os.getenv('ES_USER', ''), password=os.getenv('ES_PASS', ''))

@dataclass
class GeminiSettings(BaseAPISettings):

    @classmethod
    def _from_env(cls) -> 'GeminiSettings':
        api_key = None
        if os.getenv('GEMINI_API_KEY'):
            api_key = SecretStr(os.getenv('GEMINI_API_KEY', ''))
        return cls(_api_key=api_key)

@dataclass
class Settings:  # pylint: disable=too-many-instance-attributes
    character: CharacterSettings
    elasticsearch: ElasticsearchSettings
    elevenlabs: ElevenLabsSettings
    embedding: EmbeddingSettings
    embedding_model: EmbeddingModelSettings
    emotion_detection: EmotionDetectionSettings
    face_clustering: FaceClusteringSettings
    face_recognition: FaceRecognitionSettings
    frame_export: FrameExportSettings
    gemini: GeminiSettings
    image_hash: ImageHashSettings
    image_scraper: ImageScraperSettings
    keyframe_extraction: KeyframeExtractionSettings
    object_detection: ObjectDetectionSettings
    output_subdirs: OutputSubdirs
    scene_detection: SceneDetectionSettings
    scraper: ScraperSettings
    text_chunking: TextChunkingSettings
    transcode: TranscodeSettings
    transcription: TranscriptionSettings
    whisper: WhisperSettings

    @classmethod
    def _from_env(cls) -> 'Settings':
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

@dataclass
class TranscodeConfig:
    codec: str
    gop_size: float
    resolution: Resolution
    transcoded_videos: Path
    videos: Path
    audio_bitrate_kbps: int = 128
    bufsize_mbps: Optional[float] = None
    episodes_info_json: Optional[Path] = None
    maxrate_mbps: Optional[float] = None
    minrate_mbps: Optional[float] = None
    video_bitrate_mbps: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'videos': self.videos,
            'transcoded_videos': self.transcoded_videos,
            'resolution': self.resolution,
            'codec': self.codec,
            'video_bitrate_mbps': self.video_bitrate_mbps,
            'minrate_mbps': self.minrate_mbps,
            'maxrate_mbps': self.maxrate_mbps,
            'bufsize_mbps': self.bufsize_mbps,
            'audio_bitrate_kbps': self.audio_bitrate_kbps,
            'gop_size': self.gop_size,
            'episodes_info_json': self.episodes_info_json,
        }

@dataclass
class TranscriptionConfig:
    device: str
    episodes_info_json: Path
    language: str
    model: str
    name: str
    transcription_jsons: Path
    videos: Path
    extra_json_keys_to_remove: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'videos': self.videos,
            'episodes_info_json': self.episodes_info_json,
            'transcription_jsons': self.transcription_jsons,
            'model': self.model,
            'language': self.language,
            'device': self.device,
            'extra_json_keys_to_remove': self.extra_json_keys_to_remove,
            'name': self.name,
        }

@dataclass
class IndexConfig:
    name: str
    transcription_jsons: Path
    append: bool = False
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {'name': self.name, 'transcription_jsons': str(self.transcription_jsons), 'dry_run': self.dry_run, 'append': self.append}
