from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    Optional,
)

from preprocessor.config.constants import (
    EpisodeMetadataKeys,
    EpisodesDataKeys,
)
from preprocessor.services.core.logging import ErrorHandlingLogger
from preprocessor.services.io.path_service import PathService


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


class EpisodeManager:
    def __init__(
            self,
            episodes_info_json: Optional[Path],
            series_name: str,
            logger: Optional[ErrorHandlingLogger] = None,
    ) -> None:
        self.__series_name = series_name.lower()
        self.__episodes_data: Optional[Dict[str, Any]] = None
        self.__path_manager = PathService(self.__series_name)
        self.__logger = logger

        self.__load_episodes_data(episodes_info_json)

    @property
    def path_manager(self) -> PathService:
        return self.__path_manager

    def get_episode_by_season_and_relative(self, season: int, relative_episode: int) -> EpisodeInfo:
        if not self.__episodes_data:
            return self.__create_fallback_episode_info(season, relative_episode)

        season_list = self.__episodes_data.get(EpisodesDataKeys.SEASONS, [])
        for season_data in season_list:
            if season_data.get(EpisodesDataKeys.SEASON_NUMBER) == season:
                return self.__extract_episode_from_season(season_data, season, relative_episode)

        self.__log_missing_season_warning(season, relative_episode)
        return self.__create_fallback_episode_info(season, relative_episode)

    def parse_filename(self, file_path: Path) -> Optional[EpisodeInfo]:
        full_path_str = str(file_path)
        match_season_episode = re.search(r'S(\d+)[/\\]?E(\d+)', full_path_str, re.IGNORECASE)

        if match_season_episode:
            season = int(match_season_episode.group(1))
            episode = int(match_season_episode.group(2))
            return self.get_episode_by_season_and_relative(season, episode)

        if self.__logger:
            self.__logger.error(
                f'Cannot parse episode from filename: {file_path.name}. '
                'Expected format: S##E## (e.g., S01E05, S10E13). '
                'Absolute episode numbers (E## without season) are not supported.',
            )
        return None

    @staticmethod
    def get_episode_id_for_state(episode_info: EpisodeInfo) -> str:
        return episode_info.episode_code()

    @staticmethod
    def get_metadata(episode_info: EpisodeInfo) -> Dict[str, Any]:
        return {
            'season': episode_info.season,
            'episode_number': episode_info.relative_episode,
            'title': episode_info.title,
            'premiere_date': episode_info.premiere_date,
            'viewership': episode_info.viewership,
        }

    def __load_episodes_data(self, json_path: Optional[Path]) -> None:
        if json_path and json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.__episodes_data = json.load(f)
            except Exception as e:
                if self.__logger:
                    self.__logger.error(f'Failed to load episodes data from {json_path}: {e}')

    def __extract_episode_from_season(
            self, season_data: Dict[str, Any], season: int, relative_episode: int,
    ) -> EpisodeInfo:
        episodes = sorted(
            season_data.get(EpisodesDataKeys.EPISODES, []),
            key=lambda ep: ep.get(EpisodeMetadataKeys.EPISODE_NUMBER, 0),
        )

        if 0 < relative_episode <= len(episodes):
            ep_data = episodes[relative_episode - 1]
            return self.__create_episode_info(
                season=season,
                relative_episode=relative_episode,
                title=ep_data.get(EpisodeMetadataKeys.TITLE),
                premiere_date=ep_data.get(EpisodeMetadataKeys.PREMIERE_DATE),
                viewership=ep_data.get(EpisodeMetadataKeys.VIEWERSHIP),
            )

        return self.__create_fallback_episode_info(season, relative_episode)

    def __log_missing_season_warning(self, season: int, relative_episode: int) -> None:
        if self.__logger:
            self.__logger.warning(
                f'Season {season} not found in episodes_info_json! '
                f'Processing S{season:02d}E{relative_episode:02d} with filename-only metadata. '
                f'Scrape episode info for season {season} to get title, premiere date, etc.',
            )

    def __create_fallback_episode_info(self, season: int, relative_episode: int) -> EpisodeInfo:
        return self.__create_episode_info(
            season=season,
            relative_episode=relative_episode,
            title=f'S{season:02d}E{relative_episode:02d}',
        )

    def __create_episode_info(
            self,
            season: int,
            relative_episode: int,
            title: Optional[str] = None,
            premiere_date: Optional[str] = None,
            viewership: Optional[str] = None,
    ) -> EpisodeInfo:
        return EpisodeInfo(
            absolute_episode=0,
            season=season,
            relative_episode=relative_episode,
            title=title or f'S{season:02d}E{relative_episode:02d}',
            series_name=self.__series_name,
            premiere_date=premiere_date,
            viewership=viewership,
        )
