from typing import (
    List,
    NotRequired,
    TypedDict,
)

from .episode import EpisodeMetadata


class BaseSegment(TypedDict):
    end: float
    id: int
    start: float
    text: str

class SegmentWithTimes(TypedDict):
    end_time: float
    episode_metadata: EpisodeMetadata
    segment_id: int
    start_time: float
    text: str
    video_path: NotRequired[str]

class SegmentWithScore(SegmentWithTimes):
    _score: float

class ElasticsearchSegment(TypedDict):
    _score: NotRequired[float]
    end: NotRequired[float]
    end_time: NotRequired[float]
    episode_info: NotRequired[EpisodeMetadata]
    episode_metadata: NotRequired[EpisodeMetadata]
    id: NotRequired[int]
    segment_id: NotRequired[int]
    start: NotRequired[float]
    start_time: NotRequired[float]
    text: str
    video_path: NotRequired[str]

class TranscriptionContext(TypedDict):
    context: List[BaseSegment]
    overall_end_time: float
    overall_start_time: float
    target: ElasticsearchSegment
