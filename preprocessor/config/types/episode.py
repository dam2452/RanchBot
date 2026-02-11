from typing import (
    Dict,
    TypedDict,
    Union,
)


class EpisodeInfo(TypedDict):
    episode_number: int
    premiere_date: str
    title: str
    viewership: Union[str, int, float]

class EpisodeMetadata(TypedDict):
    episode_number: int
    premiere_date: str
    season: int
    series_name: str
    title: str
    viewership: Union[str, int, float]

class SeasonInfo(TypedDict):
    pass
SeasonInfoDict = Dict[str, int]
