from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.core.path_manager import PathManager
from preprocessor.episodes.episode_file_finder import EpisodeFileFinder
from preprocessor.episodes.episode_parser import EpisodeInfoParser
from preprocessor.utils.constants import (
    EpisodeMetadataKeys,
    EpisodesDataKeys,
)

logger = logging.getLogger(__name__)


@dataclass
class EpisodeInfo:
    absolute_episode: int
    season: int
    relative_episode: int
    title: str
    series_name: Optional[str] = None
    premiere_date: Optional[str] = None
    viewership: Optional[str] = None

    def episode_code(self) -> str:
        return f"S{self.season:02d}E{self.relative_episode:02d}"

    def season_dir_name(self) -> str:
        return f"S{self.season:02d}"

    def season_code(self) -> str:
        return f"S{self.season:02d}"

    def episode_num(self) -> str:
        return f"E{self.relative_episode:02d}"

    def is_special(self) -> bool:
        return self.season == 0

    @staticmethod
    def create_minimal(season: int, episode: int, series_name: str) -> "EpisodeInfo":
        return EpisodeInfo(
            absolute_episode=0,
            season=season,
            relative_episode=episode,
            title="",
            series_name=series_name,
        )


class EpisodeManager:
    def __init__(self, episodes_info_json: Optional[Path], series_name: str):
        self.series_name = series_name.lower()
        self.episodes_data: Optional[Dict[str, Any]] = None
        self.path_manager = PathManager(self.series_name)
        self.file_finder = EpisodeFileFinder(self.series_name)
        self.parser = EpisodeInfoParser()

        if episodes_info_json and episodes_info_json.exists():
            with open(episodes_info_json, "r", encoding="utf-8") as f:
                self.episodes_data = json.load(f)

    def parse_filename(self, file_path: Path) -> Optional[EpisodeInfo]:
        return self.parser.parse_filename(file_path, self)

    def get_episode_by_season_and_relative(self, season: int, relative_episode: int) -> Optional[EpisodeInfo]:
        if not self.episodes_data:
            return EpisodeInfo(
                absolute_episode=0,
                season=season,
                relative_episode=relative_episode,
                title=f"S{season:02d}E{relative_episode:02d}",
                series_name=self.series_name,
            )

        for season_data in self.episodes_data.get(EpisodesDataKeys.SEASONS, []):
            if season_data.get(EpisodesDataKeys.SEASON_NUMBER) == season:
                episodes = sorted(
                    season_data.get(EpisodesDataKeys.EPISODES, []),
                    key=lambda ep: ep.get(EpisodeMetadataKeys.EPISODE_NUMBER, 0),
                )

                if 0 < relative_episode <= len(episodes):
                    ep_data = episodes[relative_episode - 1]
                    return EpisodeInfo(
                        absolute_episode=0,
                        season=season,
                        relative_episode=relative_episode,
                        title=ep_data.get(EpisodeMetadataKeys.TITLE, f"S{season:02d}E{relative_episode:02d}"),
                        series_name=self.series_name,
                        premiere_date=ep_data.get(EpisodeMetadataKeys.PREMIERE_DATE),
                        viewership=ep_data.get(EpisodeMetadataKeys.VIEWERSHIP),
                    )

        logger.warning(
            f"Season {season} not found in episodes_info_json! "
            f"Processing S{season:02d}E{relative_episode:02d} with filename-only metadata. "
            f"Scrape episode info for season {season} to get title, premiere date, etc.",
        )

        return EpisodeInfo(
            absolute_episode=0,
            season=season,
            relative_episode=relative_episode,
            title=f"S{season:02d}E{relative_episode:02d}",
            series_name=self.series_name,
        )


    def find_transcription_file(self, episode_info: EpisodeInfo, search_dir: Path, prefer_segmented: bool = True) -> Optional[Path]:
        return self.file_finder.find_transcription_file(episode_info, search_dir, prefer_segmented)

    @staticmethod
    def find_scene_timestamps_file(episode_info: EpisodeInfo, search_dir: Path) -> Optional[Path]:
        finder = EpisodeFileFinder("")
        return finder.find_scene_timestamps_file(episode_info, search_dir)

    @staticmethod
    def load_scene_timestamps(episode_info: EpisodeInfo, search_dir: Optional[Path], _logger=None) -> Optional[List[Dict[str, Any]]]:
        return EpisodeFileFinder.load_scene_timestamps(episode_info, search_dir, _logger)

    @staticmethod
    def get_metadata(episode_info: EpisodeInfo) -> Dict[str, Any]:
        return {
            "season": episode_info.season,
            "episode_number": episode_info.relative_episode,
            "title": episode_info.title,
            "premiere_date": episode_info.premiere_date,
            "viewership": episode_info.viewership,
        }

    @staticmethod
    def get_episode_id_for_state(episode_info: EpisodeInfo) -> str:
        return EpisodeInfoParser.get_episode_id(episode_info)

    def list_all_episodes(self) -> List[EpisodeInfo]:
        episodes = []

        if not self.episodes_data:
            return episodes

        for season_data in self.episodes_data.get(EpisodesDataKeys.SEASONS, []):
            season_num = season_data.get(EpisodesDataKeys.SEASON_NUMBER, 1)
            season_episodes = sorted(
                season_data.get(EpisodesDataKeys.EPISODES, []),
                key=lambda ep: ep.get(EpisodeMetadataKeys.EPISODE_NUMBER, 0),
            )

            for idx, ep_data in enumerate(season_episodes):
                episodes.append(
                    EpisodeInfo(
                        absolute_episode=0,
                        season=season_num,
                        relative_episode=idx + 1,
                        title=ep_data.get(EpisodeMetadataKeys.TITLE, f"S{season_num:02d}E{idx + 1:02d}"),
                        series_name=self.series_name,
                        premiere_date=ep_data.get(EpisodeMetadataKeys.PREMIERE_DATE),
                        viewership=ep_data.get(EpisodeMetadataKeys.VIEWERSHIP),
                    ),
                )

        return episodes
