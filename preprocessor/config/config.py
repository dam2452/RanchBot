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


@dataclass
class WhisperSettings:
    model: str = "large-v3-turbo"

    @classmethod
    def from_env(cls) -> "WhisperSettings":
        return cls(
            model=os.getenv("WHISPER_MODEL", "large-v3-turbo"),
        )


@dataclass
class EmbeddingSettings:
    model_name: str = "Alibaba-NLP/gme-Qwen2-VL-2B-Instruct"
    default_output_dir: Path = Path("/app/output_data/embeddings")
    segments_per_embedding: int = 5
    keyframe_strategy: str = "scene_changes"
    keyframe_interval: int = 1
    frames_per_scene: int = 1
    batch_size: int = 32
    resize_height: int = 480
    prefetch_chunks: int = 0
    video_chunk_size: int = 256
    resize_batch_size: int = 32
    color_diff_threshold: float = 0.3
    scene_fps_default: float = 30.0
    keyframe_interval_multiplier: int = 5


@dataclass
class SceneDetectionSettings:
    threshold: float = 0.5
    min_scene_len: int = 10
    output_dir: Path = Path("/app/output_data/scene_timestamps")


@dataclass
class ScraperSettings:
    output_dir: Path = Path("/app/output_data/scraped_pages")


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
class TranscodeDefaults:
    output_dir: Path = Path("/app/output_data/transcoded_videos")
    codec: str = "h264_nvenc"
    preset: str = "slow"
    crf: int = 31
    gop_size: float = 0.5
    max_workers: int = 1


@dataclass
class TranscriptionDefaults:
    output_dir: Path = Path("/app/output_data/transcriptions")
    model: str = "large-v3-turbo"
    language: str = "Polish"
    device: str = "cuda"


@dataclass
class Settings:
    whisper: WhisperSettings
    embedding: EmbeddingSettings
    scene_detection: SceneDetectionSettings
    scraper: ScraperSettings
    elevenlabs: ElevenLabsSettings
    elasticsearch: ElasticsearchSettings
    transcode: TranscodeDefaults
    transcription: TranscriptionDefaults

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            whisper=WhisperSettings.from_env(),
            embedding=EmbeddingSettings(),
            scene_detection=SceneDetectionSettings(),
            scraper=ScraperSettings(),
            elevenlabs=ElevenLabsSettings.from_env(),
            elasticsearch=ElasticsearchSettings.from_env(),
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
            "transcription_jsons": self.transcription_jsons,
            "dry_run": self.dry_run,
            "append": self.append,
        }
