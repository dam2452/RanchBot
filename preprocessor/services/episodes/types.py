from dataclasses import dataclass
from typing import Optional


@dataclass
class EpisodeInfo:
    absolute_episode: int
    relative_episode: int
    season: int
    title: str
    premiere_date: Optional[str] = None
    series_name: Optional[str] = None
    viewership: Optional[str] = None

    def episode_code(self) -> str:
        return f'S{self.season:02d}E{self.relative_episode:02d}'

    def episode_num(self) -> str:
        return f'E{self.relative_episode:02d}'

    def season_code(self) -> str:
        return f'S{self.season:02d}'

    def is_special(self) -> bool:
        return self.season == 0
