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
    end_time: float
    episode_number: int
    season: int
    start_time: float
    title: str

class ElasticsearchHit(TypedDict):
    _score: float
    _source: ElasticsearchSegment

class ElasticsearchHits(TypedDict):
    hits: List[ElasticsearchHit]
    max_score: float
    total: Dict[str, Any]

class ElasticsearchResponse(TypedDict):
    aggregations: NotRequired[Dict[str, Any]]
    hits: ElasticsearchHits
    timed_out: bool
    took: int

class EpisodeBucket(TypedDict):
    doc_count: int
    episode_metadata: Dict[str, Any]
    key: int

class SeasonBucket(TypedDict):
    doc_count: int
    key: int
    unique_episodes: Dict[str, int]

class ElasticsearchAggregations(TypedDict):
    buckets: NotRequired[List[Union[SeasonBucket, EpisodeBucket]]]
    seasons: Dict[str, Union[List[SeasonBucket], int]]
    unique_episodes: Dict[str, Union[List[EpisodeBucket], int]]
