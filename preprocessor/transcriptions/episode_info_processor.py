import json
from pathlib import Path
from typing import Optional

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
            self.__episodes_info: dict = json.load(f)
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
            with transcription_file.open("r", encoding="utf-8") as f:
                transcription = json.load(f)
            absolute_episode = self.__get_episode_number(transcription_file)
            if absolute_episode is None:
                self.__logger.error(f"Cannot extract episode number from {transcription_file.name}")
                return
            episode_info = self.__find_episode_info(absolute_episode)
            if not episode_info:
                self.__logger.error(f"No episode info found for episode {absolute_episode} in {transcription_file}")
                return
            season_number = episode_info["season"]
            relative_episode = episode_info["episode_number"]  # teraz relatywny numer
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

            new_src = transcription_file.parent / new_json_name
            if transcription_file.name == new_json_name:
                self.__logger.info(f"File {transcription_file} already has correct name.")
            elif new_src.exists():
                self.__logger.error(f"Cannot rename {transcription_file} -> {new_src}, file already exists!")
            else:
                transcription_file.rename(new_src)
                self.__logger.info(f"Renamed source transcription file: {transcription_file} -> {new_src}")

        except Exception as e:
            self.__logger.error(f"Error processing file {transcription_file}: {e}")

    def __find_episode_info(self, absolute_episode: int) -> Optional[dict]:
        # Przeszukaj każdy sezon w episodes_info.json
        for season_str, season_data in self.__episodes_info.items():
            episodes = season_data.get("episodes", [])
            episodes = sorted(episodes, key=lambda ep: ep["episode_number"])
            for idx, ep_data in enumerate(episodes):
                if ep_data.get("episode_number") == absolute_episode:
                    return {
                        "season": int(season_str),
                        "episode_number": idx + 1,  # numer relatywny
                        "premiere_date": ep_data["premiere_date"],
                        "title": ep_data["title"],
                        "viewership": ep_data["viewership"],
                    }
        return None

    @staticmethod
    def __get_episode_number(transcription_file: Path) -> Optional[int]:
        import re
        pattern = r"(?:E(?P<ep>\d+))|(?:_S\d{2}E(?P<ep2>\d+))"
        match = re.search(pattern, transcription_file.stem, re.IGNORECASE)
        if match:
            episode = match.group("ep") or match.group("ep2")
            return int(episode)
        return None
