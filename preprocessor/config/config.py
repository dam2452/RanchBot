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

from bot.utils.resolution import Resolution


class Settings:  # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self._eleven_api_key = SecretStr(os.getenv("ELEVEN_API_KEY", "")) if os.getenv("ELEVEN_API_KEY") else None

        self.whisper_model: str = os.getenv("WHISPER_MODEL", "large-v3-turbo")

        self.embedding_model_name: str = "Alibaba-NLP/gme-Qwen2-VL-2B-Instruct"

        self.embedding_default_output_dir: Path = Path("/app/output_data/embeddings")
        self.embedding_segments_per_embedding: int = 5
        self.embedding_keyframe_strategy: str = "scene_changes"
        self.embedding_keyframe_interval: int = 1
        self.embedding_frames_per_scene: int = 1
        self.embedding_max_workers: int = 1
        self.embedding_batch_size: int = 16
        self.embedding_resize_height: int = 720
        self.embedding_prefetch_chunks: int = 0

        self.scene_detection_threshold: float = 0.5
        self.scene_detection_min_scene_len: int = 10
        self.scene_detection_output_dir: Path = Path("/app/output_data/scene_timestamps")

        self.scraper_output_dir: Path = Path("/app/output_data/scraped_pages")

        self.elevenlabs_model_id: str = "scribe_v1"
        self.elevenlabs_language_code: str = "pol"
        self.elevenlabs_diarize: bool = True
        self.elevenlabs_diarization_threshold: float = 0.4
        self.elevenlabs_temperature: float = 0.0
        self.elevenlabs_polling_interval: int = 20
        self.elevenlabs_max_attempts: int = 60

    @property
    def eleven_api_key(self) -> Optional[str]:
        return self._eleven_api_key.get_secret_value() if self._eleven_api_key else None


settings = Settings()


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