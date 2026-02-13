from pathlib import Path
from typing import (
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from preprocessor.config.enums import KeyframeStrategy
from preprocessor.services.media.resolution import Resolution


class TranscodeConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    bitrate_reference_mb: float = Field(gt=0)
    bitrate_reference_seconds: float = Field(gt=0)
    force_deinterlace: bool = False
    keyframe_interval_seconds: float = Field(gt=0)
    resolution: Resolution = Field(default=Resolution.R720P)

    @property
    def audio_bitrate_kbps(self) -> int:
        return 128

    @property
    def codec(self) -> str:
        return 'h264_nvenc'

    @property
    def preset(self) -> str:
        return 'p7'

    @property
    def video_bitrate_mbps(self) -> float:
        total = (self.bitrate_reference_mb * 8) / self.bitrate_reference_seconds
        audio = self.audio_bitrate_kbps / 1000.0
        return round(total - audio, 2)

    def calculate_minrate_mbps(self, percent: float = 0.6) -> float:
        return round(self.video_bitrate_mbps * percent, 2)

    def calculate_maxrate_mbps(self, percent: float = 1.4) -> float:
        return round(self.video_bitrate_mbps * percent, 2)

    def calculate_bufsize_mbps(self, multiplier: float = 2.0) -> float:
        return round(self.video_bitrate_mbps * multiplier, 2)


class SceneDetectionConfig(BaseModel):
    min_scene_len: int = Field(default=10, ge=1)
    threshold: float = Field(default=0.5, ge=0, le=1)


class FrameExportConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    frames_per_scene: int = Field(default=3, ge=1)
    keyframe_strategy: KeyframeStrategy = KeyframeStrategy.SCENE_CHANGES
    resolution: Resolution = Field(default=Resolution.R720P)


class TranscriptionConfig(BaseModel):
    language: str = 'pl'
    model: str = 'large-v3'
    output_formats: List[str] = ['json', 'srt', 'txt']


class WhisperTranscriptionConfig(BaseModel):
    beam_size: int = Field(default=10, ge=1)
    device: str = 'cuda'
    language: str = 'pl'
    model: str = 'large-v3-turbo'
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)


class TextAnalysisConfig(BaseModel):
    language: str = 'pl'


class TextEmbeddingConfig(BaseModel):
    batch_size: int = Field(default=8, ge=1)
    device: str = 'cuda'
    model_name: str = 'Qwen/Qwen3-VL-Embedding-8B'
    text_chunk_overlap: int = Field(default=1, ge=0)
    text_sentences_per_chunk: int = Field(default=5, ge=1)


class VideoEmbeddingConfig(BaseModel):
    batch_size: int = Field(default=8, ge=1)
    device: str = 'cuda'
    model_name: str = 'Qwen/Qwen3-VL-Embedding-8B'


class SoundSeparationConfig(BaseModel):
    pass


class DocumentGenerationConfig(BaseModel):
    generate_segments: bool = True


class ImageHashConfig(BaseModel):
    batch_size: int = Field(default=32, ge=1)


class TranscriptionImportConfig(BaseModel):
    format_type: str = '11labs_segmented'
    source_dir: str


class ElasticsearchConfig(BaseModel):
    append: bool = False
    dry_run: bool = False
    host: str = 'localhost:9200'
    index_name: str


class AudioExtractionConfig(BaseModel):
    pass


class CharacterDetectionConfig(BaseModel):
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class EmotionDetectionConfig(BaseModel):
    pass


class FaceClusteringConfig(BaseModel):
    pass


class ObjectDetectionConfig(BaseModel):
    pass


class ArchiveConfig(BaseModel):
    pass


class ValidationConfig(BaseModel):
    anomaly_threshold: float = 20.0
    episodes_info_json: Optional[Path] = None


class EpisodeScraperConfig(BaseModel):
    headless: bool = True
    merge_sources: bool = True
    output_file: str
    parser_mode: str = "normal"
    scraper_method: str = "crawl4ai"
    urls: List[str]


class CharacterScraperConfig(BaseModel):
    headless: bool = True
    output_file: str
    parser_mode: str = "normal"
    scraper_method: str = "crawl4ai"
    urls: List[str]


class CharacterReferenceConfig(BaseModel):
    characters_file: str
    images_per_character: int = Field(default=5, ge=1, le=20)
    output_dir: str
    search_engine: str = "duckduckgo"
