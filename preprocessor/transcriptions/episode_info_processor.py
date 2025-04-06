import json
from pathlib import Path
import re
from typing import (
    Optional,
    Tuple,
)

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class EpisodeInfoProcessor:
    def __init__(
        self,
        jsons_dir: Path,
        episodes_info_json: Path,
        output_path: Path,
        logger: ErrorHandlingLogger,
        series_name: str = "",
    ):
        self.__jsons_dir: Path = jsons_dir
        with open(episodes_info_json, "r", encoding="utf-8") as f:
            self.__episodes_info: json = json.load(f)
        self.__output_path: Path = output_path
        self.__logger: ErrorHandlingLogger = logger
        if not series_name:
            series_name = self.__output_path.parent.name.lower()
        self.__series_name: str = series_name.lower()
        self.__output_path.mkdir(parents=True, exist_ok=True)

    def __call__(self) -> None:
        for transcription_file in self.__jsons_dir.rglob("*"):
            if transcription_file.is_file() and transcription_file.suffix == ".json":
                self.__process_file(transcription_file)

    def __process_file(self, transcription_file: Path) -> None:
        try:
            transcription = self.__load_transcription(transcription_file)
            absolute_episode = self.__get_episode_number(transcription_file)
            if absolute_episode is None:
                self.__logger.error(f"Cannot extract episode number from {transcription_file.name}")
                return

            episode_info = self.__find_episode_info(absolute_episode)
            if not episode_info:
                self.__logger.error(f"No episode info found for episode {absolute_episode} in {transcription_file}")
                return

            _, new_json_name = self.__write_episode_json(transcription, episode_info)
            self.__rename_original_file(transcription_file, new_json_name)

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.__logger.error(f"Error processing file {transcription_file}: {e}")

    @staticmethod
    def __load_transcription(path: Path) -> json:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def __write_episode_json(self, transcription: json, episode_info: json) -> Tuple[Path, str]:
        season_number = episode_info["season"]
        relative_episode = episode_info["episode_number"]
        new_json_name = f"{self.__series_name}_S{season_number:02d}E{relative_episode:02d}.json"

        output_dir = self.__output_path / f"Sezon {season_number}"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / new_json_name
        result = {
            "episode_info": episode_info,
            "segments": transcription.get("segments", []),
        }

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        self.__logger.info(f"Created episode info {output_path}.")
        return output_path, new_json_name

    def __rename_original_file(self, original_path: Path, new_name: str) -> None:
        new_src = original_path.parent / new_name
        if original_path.name == new_name:
            self.__logger.info(f"File {original_path} already has correct name.")
        elif new_src.exists():
            self.__logger.error(f"Cannot rename {original_path} -> {new_src}, file already exists!")
        else:
            original_path.rename(new_src)
            self.__logger.info(f"Renamed source transcription file: {original_path} -> {new_src}")

    def __find_episode_info(self, absolute_episode: int) -> Optional[json]:

        for season_str, season_data in self.__episodes_info.items():
            episodes = season_data.get("episodes", [])
            episodes = sorted(episodes, key=lambda ep: ep["episode_number"])
            for idx, ep_data in enumerate(episodes):
                if ep_data.get("episode_number") == absolute_episode:
                    return {
                        "season": int(season_str),
                        "episode_number": idx + 1,
                        "premiere_date": ep_data["premiere_date"],
                        "title": ep_data["title"],
                        "viewership": ep_data["viewership"],
                    }
        return None

    @staticmethod
    def __get_episode_number(transcription_file: Path) -> Optional[int]:
        pattern = r"(?:E(?P<ep>\d+))|(?:_S\d{2}E(?P<ep2>\d+))"
        match = re.search(pattern, transcription_file.stem, re.IGNORECASE)
        if match:
            episode = match.group("ep") or match.group("ep2")
            return int(episode)
        return None
