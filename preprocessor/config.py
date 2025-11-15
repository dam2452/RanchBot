from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from bot.utils.resolution import Resolution


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

    def to_dict(self) -> Dict:
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

    def to_dict(self) -> Dict:
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

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "transcription_jsons": self.transcription_jsons,
            "dry_run": self.dry_run,
            "append": self.append,
        }
