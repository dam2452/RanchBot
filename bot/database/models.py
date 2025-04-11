from dataclasses import dataclass
from datetime import (
    date,
    datetime,
)
from enum import Enum
from pathlib import Path
from typing import Optional

from bot.database.serializable import Serializable


@dataclass
class UserProfile(Serializable):
    user_id: int
    username: Optional[str]
    full_name: Optional[str]
    subscription_end: Optional[date]
    note: Optional[str]


@dataclass
class VideoClip(Serializable):
    id: int
    chat_id: int
    user_id: int
    name: str
    video_data: bytes
    start_time: float
    end_time: float
    duration: float
    season: Optional[int]
    episode_number: Optional[int]
    is_compilation: bool


class ClipType(Enum):
    MANUAL = "manual"
    COMPILED = "compiled"
    SELECTED = "selected"
    ADJUSTED = "adjusted"
    SINGLE = "single"


@dataclass
class LastClip(Serializable):
    id: int
    chat_id: int
    segment: str
    compiled_clip: Optional[bytes]
    clip_type: Optional[ClipType]
    adjusted_start_time: Optional[float]
    adjusted_end_time: Optional[float]
    is_adjusted: bool
    timestamp: date


@dataclass
class SearchHistory(Serializable):
    id: int
    chat_id: int
    quote: str
    segments: str


@dataclass(frozen=True)
class FormattedSegmentInfo:
    episode_formatted: str
    time_formatted: str
    episode_title: str

@dataclass
class SubscriptionKey(Serializable):
    id: int
    key: str
    days: int
    is_active: bool
    timestamp: Optional[datetime] = None

@dataclass
class ClipInfo(Serializable):
    output_filename: Path
    start_time: float
    end_time: float
    is_compilation: bool
    season: Optional[int]
    episode_number: Optional[int]
