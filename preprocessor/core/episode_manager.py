from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.core.constants import SUPPORTED_VIDEO_EXTENSIONS


@dataclass
class EpisodeInfo:
    absolute_episode: int
    season: int
    relative_episode: int
    title: str
    premiere_date: Optional[str] = None
    viewership: Optional[str] = None

    def episode_code(self) -> str:
        return f"S{self.season:02d}E{self.relative_episode:02d}"

    def season_dir_name(self) -> str:
        return "Specjalne" if self.season == 0 else f"Sezon {self.season}"

    def is_special(self) -> bool:
        return self.season == 0


class EpisodeManager:
    def __init__(self, episodes_info_json: Optional[Path], series_name: str):
        self.series_name = series_name.lower()
        self.episodes_data: Optional[Dict[str, Any]] = None

        if episodes_info_json and episodes_info_json.exists():
            with open(episodes_info_json, "r", encoding="utf-8") as f:
                self.episodes_data = json.load(f)

    def parse_filename(self, file_path: Path) -> Optional[EpisodeInfo]:
        match_absolute = re.search(r'E(\d+)', file_path.name, re.IGNORECASE)
        if match_absolute:
            absolute = int(match_absolute.group(1))
            return self.parse_absolute_episode(absolute)

        match_season_episode = re.search(r'S(\d+)E(\d+)', file_path.name, re.IGNORECASE)
        if match_season_episode:
            season = int(match_season_episode.group(1))
            episode = int(match_season_episode.group(2))
            return self.get_episode_by_season_and_relative(season, episode)

        return None

    def parse_absolute_episode(self, absolute: int) -> Optional[EpisodeInfo]:
        if not self.episodes_data:
            return EpisodeInfo(
                absolute_episode=absolute,
                season=1,
                relative_episode=absolute,
                title=f"Episode {absolute}",
            )

        for season in self.episodes_data.get("seasons", []):
            season_num = season.get("season_number", 1)
            episodes = sorted(season.get("episodes", []), key=lambda ep: ep["episode_number"])

            for idx, ep_data in enumerate(episodes):
                if ep_data.get("episode_number") == absolute:
                    return EpisodeInfo(
                        absolute_episode=absolute,
                        season=season_num,
                        relative_episode=idx + 1,
                        title=ep_data.get("title", f"Episode {absolute}"),
                        premiere_date=ep_data.get("premiere_date"),
                        viewership=ep_data.get("viewership"),
                    )

        return None

    def get_episode_by_season_and_relative(self, season: int, relative_episode: int) -> Optional[EpisodeInfo]:
        if not self.episodes_data:
            return EpisodeInfo(
                absolute_episode=relative_episode,
                season=season,
                relative_episode=relative_episode,
                title=f"Episode {relative_episode}",
            )

        for season_data in self.episodes_data.get("seasons", []):
            if season_data.get("season_number") == season:
                episodes = sorted(season_data.get("episodes", []), key=lambda ep: ep.get("episode_number", 0))

                if 0 < relative_episode <= len(episodes):
                    ep_data = episodes[relative_episode - 1]
                    return EpisodeInfo(
                        absolute_episode=ep_data.get("episode_number", relative_episode),
                        season=season,
                        relative_episode=relative_episode,
                        title=ep_data.get("title", f"Episode {relative_episode}"),
                        premiere_date=ep_data.get("premiere_date"),
                        viewership=ep_data.get("viewership"),
                    )

        return None

    def build_output_path(self, episode_info: EpisodeInfo, base_dir: Path, extension: str = ".mp4") -> Path:
        filename = f"{self.series_name}_{episode_info.episode_code()}{extension}"
        season_dir = base_dir / episode_info.season_dir_name()
        season_dir.mkdir(parents=True, exist_ok=True)
        return season_dir / filename

    def build_video_path_for_elastic(self, episode_info: EpisodeInfo) -> str:
        filename = f"{self.series_name}_{episode_info.episode_code()}.mp4"
        path = Path("bot") / f"{self.series_name.upper()}-WIDEO" / episode_info.season_dir_name() / filename
        return path.as_posix()

    @staticmethod
    def find_video_file(episode_info: EpisodeInfo, search_dir: Path) -> Optional[Path]:
        if not search_dir.exists():
            return None

        if search_dir.is_file():
            return search_dir


        episode_code = episode_info.episode_code()
        search_dirs = [search_dir / episode_info.season_dir_name(), search_dir]

        for dir_path in search_dirs:
            if not dir_path.exists():
                continue

            for ext in SUPPORTED_VIDEO_EXTENSIONS:
                for video_file in dir_path.glob(f"*{ext}"):
                    if re.search(episode_code, video_file.name, re.IGNORECASE):
                        return video_file

        return None

    def find_transcription_file(self, episode_info: EpisodeInfo, search_dir: Path, prefer_segmented: bool = True) -> Optional[Path]:
        if not search_dir.exists():
            return None

        season_dir = search_dir / episode_info.season_dir_name()
        if not season_dir.exists():
            return None

        base_name = f"{self.series_name}_{episode_info.episode_code()}"

        if prefer_segmented:
            segmented = season_dir / f"{base_name}_segmented.json"
            if segmented.exists():
                return segmented

        regular = season_dir / f"{base_name}.json"
        if regular.exists():
            return regular

        return None

    @staticmethod
    def find_scene_timestamps_file(episode_info: EpisodeInfo, search_dir: Path) -> Optional[Path]:
        if not search_dir.exists():
            return None

        episode_code = episode_info.episode_code()
        pattern = f"*{episode_code}*_scenes.json"

        for scene_file in search_dir.glob(pattern):
            return scene_file

        return None

    @staticmethod
    def load_scene_timestamps(episode_info: EpisodeInfo, search_dir: Optional[Path], logger=None) -> Optional[List[Dict[str, Any]]]:
        if not search_dir:
            return None
        scene_file = EpisodeManager.find_scene_timestamps_file(episode_info, search_dir)
        if not scene_file:
            return None
        try:
            with open(scene_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            if logger:
                logger.error(f"Failed to load scene timestamps: {e}")
            return None

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
        return f"E{episode_info.absolute_episode}"

    def list_all_episodes(self) -> List[EpisodeInfo]:
        episodes = []

        if not self.episodes_data:
            return episodes

        for season_data in self.episodes_data.get("seasons", []):
            season_num = season_data.get("season_number", 1)
            season_episodes = sorted(
                season_data.get("episodes", []),
                key=lambda ep: ep.get("episode_number", 0),
            )

            for idx, ep_data in enumerate(season_episodes):
                episodes.append(
                    EpisodeInfo(
                        absolute_episode=ep_data.get("episode_number", idx + 1),
                        season=season_num,
                        relative_episode=idx + 1,
                        title=ep_data.get("title", f"Episode {idx + 1}"),
                        premiere_date=ep_data.get("premiere_date"),
                        viewership=ep_data.get("viewership"),
                    ),
                )

        return episodes
