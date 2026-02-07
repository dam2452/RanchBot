from typing import (
    Any,
    Dict,
    List,
    NotRequired,
    TypedDict,
    Union,
)


class EpisodeInfo(TypedDict):
    episode_number: int
    title: str
    premiere_date: str
    viewership: Union[str, int, float]


class EpisodeMetadata(TypedDict):
    season: int
    episode_number: int
    title: str
    premiere_date: str
    viewership: Union[str, int, float]
    series_name: str


class SeasonInfo(TypedDict):
    pass


SeasonInfoDict = Dict[str, int]


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


class ClipSegment(TypedDict):
    video_path: Union[str, Any]
    start_time: float
    end_time: float


class SearchSegment(TypedDict):
    season: int
    episode_number: int
    title: str
    start_time: float
    end_time: float


class ElasticsearchHit(TypedDict):
    _source: ElasticsearchSegment
    _score: float


class ElasticsearchHits(TypedDict):
    hits: List[ElasticsearchHit]
    total: Dict[str, Any]
    max_score: float


class ElasticsearchResponse(TypedDict):
    hits: ElasticsearchHits
    aggregations: NotRequired[Dict[str, Any]]
    took: int
    timed_out: bool


class EpisodeBucket(TypedDict):
    key: int
    doc_count: int
    episode_metadata: Dict[str, Any]


class SeasonBucket(TypedDict):
    key: int
    doc_count: int
    unique_episodes: Dict[str, int]


class ElasticsearchAggregations(TypedDict):
    seasons: Dict[str, Union[List[SeasonBucket], int]]
    unique_episodes: Dict[str, Union[List[EpisodeBucket], int]]
    buckets: NotRequired[List[Union[SeasonBucket, EpisodeBucket]]]
