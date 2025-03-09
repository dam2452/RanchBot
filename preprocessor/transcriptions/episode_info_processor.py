import json
from pathlib import Path
import re
from typing import Optional

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class EpisodeInfoProcessor:
    def __init__(self, jsons_dir: Path, episodes_info_json: Path, output_path: Path, logger: ErrorHandlingLogger):
        self.__jsons_dir: Path = jsons_dir

        with open(episodes_info_json, "r", encoding="utf-8") as f:
            self.__episodes_info: json = json.load(f)

        self.__output_path: Path = output_path
        self.__logger: ErrorHandlingLogger = logger

        self.__output_path.mkdir(parents=True, exist_ok=True)

    def __call__(self) -> None:
        for episode in self.__jsons_dir.rglob("*"):
            self.__process_file(episode)

    def __process_file(self, episode: Path) -> None:
        try:
            episode_info = self.__find_episode_info(episode)
            if not episode_info:
                self.__logger.error(f"No episode info for {episode}. Skipping...")
                return

            with open(episode_info, "r", encoding="utf-8") as f:
                transcription = json.load(f)

            result = {
                "episode_info": episode_info,
                "segments": transcription.get("segments", []),
            }

            output_path = self.__output_path.joinpath(episode.name)

            with output_path.open("w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=4)

            self.__logger.info(f"Created episode info {output_path}.")

        except Exception as e: # pylint: disable=broad-exception-caught
            self.__logger.error(f"Error processing file {episode}: {e}")

    def __find_episode_info(self, episode: Path) -> Optional[json]:
        for season_str, data in self.__episodes_info.items():
            for ep_data in data.get("episodes", []):
                if ep_data.get("episode_number") == self.__get_episode_number(episode):
                    return {
                        "season": int(season_str),
                        "episode_number": ep_data["episode_number"],
                        "premiere_date": ep_data["premiere_date"],
                        "title": ep_data["title"],
                        "viewership": ep_data["viewership"],
                    }
        return None

    @staticmethod
    def __get_episode_number(episode: Path) -> Optional[int]:
        pattern = r"E(?P<episode>\d{3})"
        match = re.search(pattern, episode.name, re.IGNORECASE)
        if match:
            return int(match.group("episode"))
        return None
