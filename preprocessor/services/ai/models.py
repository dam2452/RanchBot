from typing import (
    Dict,
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
    premiere_date: Optional[str] = None
    title: str
    viewership: Optional[str] = None

    @field_validator('viewership', mode='before')
    @classmethod
    def _convert_viewership_to_str(cls, v: Optional[int]) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, int):
            return str(v)
        return v


class SeasonMetadata(BaseModel):
    episodes: List[EpisodeInfo]
    season_number: int

    @model_validator(mode='before')
    @classmethod
    def _convert_old_format(cls, data: Dict) -> Dict:
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
    description: str
    episode_number: Optional[int] = None
    season: Optional[int] = None
    summary: str
    title: str


class CharacterInfo(BaseModel):
    name: str


class CharactersList(BaseModel):
    characters: List[CharacterInfo]
