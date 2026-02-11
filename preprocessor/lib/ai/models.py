from typing import (
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
)


class EpisodeInfo(BaseModel):
    episode_in_season: int
    overall_episode_number: int
    title: str
    premiere_date: Optional[str] = None
    viewership: Optional[str] = None

    @field_validator('viewership', mode='before')
    @classmethod
    @staticmethod
    def __convert_viewership_to_str(cls, v: Optional[int]) -> Optional[str]:
 # pylint: disable=unused-private-member
        if v is None:
            return None
        if isinstance(v, int):
            return str(v)
        return v


class SeasonMetadata(BaseModel):
    season_number: int
    episodes: List[EpisodeInfo]

    @model_validator(mode='before')
    @classmethod
    @staticmethod
    def __convert_old_format(cls, data: dict) -> dict:
 # pylint: disable=unused-private-member # pylint: disable=unused-private-member
        if isinstance(data, dict) and 'episodes' in data:
            for idx, episode in enumerate(data['episodes'], start=1):
                if isinstance(episode, dict) and 'episode_number' in episode and ('episode_in_season' not in episode):
                    episode['episode_in_season'] = idx
                    episode['overall_episode_number'] = episode['episode_number']
                    del episode['episode_number']
        return data


class AllSeasonsMetadata(BaseModel):
    seasons: List[SeasonMetadata]


class EpisodeMetadata(BaseModel):
    title: str
    description: str
    summary: str
    season: Optional[int] = None
    episode_number: Optional[int] = None


class CharacterInfo(BaseModel):
    name: str


class CharactersList(BaseModel):
    characters: List[CharacterInfo]
