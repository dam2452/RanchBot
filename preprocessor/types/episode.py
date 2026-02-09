from typing import (
    Dict,
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
