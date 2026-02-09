from typing import (
    Any,
    Dict,
    List,
    NotRequired,
    TypedDict,
    Union,
)

from .transcription import ElasticsearchSegment


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
