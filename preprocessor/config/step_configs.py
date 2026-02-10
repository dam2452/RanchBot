from typing import List

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)
from typing_extensions import Self

from preprocessor.config.enums import KeyframeStrategy
from preprocessor.lib.media.resolution import Resolution


class TranscodeConfig(BaseModel):
    resolution: Resolution = Field(default=Resolution.R720P)
    codec: str = Field(default='h264_nvenc')
    preset: str = 'p7'
    video_bitrate_mbps: float = Field(gt=0)
    minrate_mbps: float = Field(gt=0)
    maxrate_mbps: float = Field(gt=0)
    bufsize_mbps: float = Field(gt=0)
    audio_bitrate_kbps: int = 128
    gop_size: float = Field(gt=0)

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode='after')
    def maxrate_must_be_greater_than_bitrate(self) -> Self:
        if self.maxrate_mbps < self.video_bitrate_mbps:
            raise ValueError('maxrate must be >= video_bitrate')
        return self

class SceneDetectionConfig(BaseModel):
    threshold: float = Field(default=0.5, ge=0, le=1)
    min_scene_len: int = Field(default=10, ge=1)

class FrameExportConfig(BaseModel):
    resolution: Resolution = Field(default=Resolution.R720P)
    keyframe_strategy: KeyframeStrategy = KeyframeStrategy.SCENE_CHANGES
    frames_per_scene: int = Field(default=3, ge=1)

    class Config:
        arbitrary_types_allowed = True

class TranscriptionConfig(BaseModel):
    model: str = 'large-v3'
    language: str = 'pl'
    output_formats: List[str] = ['json', 'srt', 'txt']

class WhisperTranscriptionConfig(BaseModel):
    model: str = 'large-v3-turbo'
    language: str = 'pl'
    device: str = 'cuda'
    beam_size: int = Field(default=10, ge=1)
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)

class TextAnalysisConfig(BaseModel):
    language: str = 'pl'

class TextEmbeddingConfig(BaseModel):
    model_name: str = 'Qwen/Qwen2-VL-8B-Instruct'
    batch_size: int = Field(default=8, ge=1)
    device: str = 'cuda'
    text_sentences_per_chunk: int = Field(default=5, ge=1)
    text_chunk_overlap: int = Field(default=1, ge=0)

class VideoEmbeddingConfig(BaseModel):
    model_name: str = 'Qwen/Qwen2-VL-8B-Instruct'
    batch_size: int = Field(default=8, ge=1)
    device: str = 'cuda'

class SoundSeparationConfig(BaseModel):
    pass

class DocumentGenerationConfig(BaseModel):
    generate_segments: bool = True

class ImageHashConfig(BaseModel):
    batch_size: int = Field(default=32, ge=1)

class TranscriptionImportConfig(BaseModel):
    source_dir: str
    format_type: str = '11labs_segmented'

class ElasticsearchConfig(BaseModel):
    index_name: str
    host: str = 'localhost:9200'
    dry_run: bool = False
    append: bool = False

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
    pass


class EpisodeScraperConfig(BaseModel):
    urls: List[str]
    output_file: str
    headless: bool = True
    merge_sources: bool = True
    scraper_method: str = "crawl4ai"
    parser_mode: str = "normal"


class CharacterScraperConfig(BaseModel):
    urls: List[str]
    output_file: str
    headless: bool = True
    scraper_method: str = "crawl4ai"
    parser_mode: str = "normal"


class CharacterReferenceConfig(BaseModel):
    characters_file: str
    output_dir: str
    search_engine: str = "duckduckgo"
    images_per_character: int = Field(default=5, ge=1, le=20)
