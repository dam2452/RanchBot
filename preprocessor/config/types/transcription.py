from typing import (
    List,
    NotRequired,
    TypedDict,
)

from .episode import EpisodeMetadata


class BaseSegment(TypedDict):
    id: int
    text: str
    start: float
    end: float

class SegmentWithTimes(TypedDict):
    segment_id: int
    text: str
    start_time: float
    end_time: float
    episode_metadata: EpisodeMetadata
    video_path: NotRequired[str]

class SegmentWithScore(SegmentWithTimes):
    _score: float

class ElasticsearchSegment(TypedDict):
    segment_id: NotRequired[int]
    id: NotRequired[int]
    text: str
    start_time: NotRequired[float]
    start: NotRequired[float]
    end_time: NotRequired[float]
    end: NotRequired[float]
    episode_metadata: NotRequired[EpisodeMetadata]
    episode_info: NotRequired[EpisodeMetadata]
    video_path: NotRequired[str]
    _score: NotRequired[float]

class TranscriptionContext(TypedDict):
    target: ElasticsearchSegment
    context: List[BaseSegment]
    overall_start_time: float
    overall_end_time: float
