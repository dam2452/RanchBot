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
    audio_bitrate_kbps: int = 128
    bufsize_mbps: float = Field(gt=0)
    codec: str = Field(default='h264_nvenc')
    force_deinterlace: bool = False
    gop_size: float = Field(gt=0)
    maxrate_mbps: float = Field(gt=0)
    minrate_mbps: float = Field(gt=0)
    preset: str = 'p7'
    resolution: Resolution = Field(default=Resolution.R720P)
    video_bitrate_mbps: float = Field(gt=0)

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode='after')
    def __maxrate_must_be_greater_than_bitrate(self) -> Self:  # pylint: disable=unused-private-member
        if self.maxrate_mbps < self.video_bitrate_mbps:
            raise ValueError('maxrate must be >= video_bitrate')
        return self

class SceneDetectionConfig(BaseModel):
    min_scene_len: int = Field(default=10, ge=1)
    threshold: float = Field(default=0.5, ge=0, le=1)

class FrameExportConfig(BaseModel):
    frames_per_scene: int = Field(default=3, ge=1)
    keyframe_strategy: KeyframeStrategy = KeyframeStrategy.SCENE_CHANGES
    resolution: Resolution = Field(default=Resolution.R720P)

    class Config:
        arbitrary_types_allowed = True

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
    pass


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
