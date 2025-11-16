import json
from pathlib import Path
import re
from typing import Optional

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.transcriptions.full_json_generator import FullJsonGenerator
from preprocessor.transcriptions.segmented_json_generator import SegmentedJsonGenerator
from preprocessor.transcriptions.simple_json_generator import SimpleJsonGenerator
from preprocessor.transcriptions.srt_generator import SrtGenerator
from preprocessor.transcriptions.txt_generator import TxtGenerator


class MultiFormatGenerator:
    def __init__(
        self,
        jsons_dir: Path,
        episodes_info_json: Path,
        output_base_path: Path,
        logger: ErrorHandlingLogger,
        series_name: str = "",
    ):
        self.jsons_dir = jsons_dir
        with open(episodes_info_json, "r", encoding="utf-8") as f:
            self.episodes_info = json.load(f)
        self.output_base_path = output_base_path
        self.logger = logger
        self.series_name = series_name.lower() if series_name else "unknown"

        self.format_dirs = {
            "json": self.output_base_path / "json",
            "segmented_json": self.output_base_path / "segmented_json",
            "simple_json": self.output_base_path / "simple_json",
            "srt": self.output_base_path / "srt",
            "txt": self.output_base_path / "txt",
        }

    def __call__(self) -> None:
        self.generate()

    def generate(self) -> None:
        for transcription_file in self.jsons_dir.rglob("*.json"):
            self._process_file(transcription_file)

    def _process_file(self, transcription_file: Path) -> None:
        try:
            with open(transcription_file, "r", encoding="utf-8") as f:
                transcription = json.load(f)

            absolute_episode = self._get_episode_number(transcription_file)
            if absolute_episode is None:
                self.logger.error(f"Cannot extract episode number from {transcription_file.name}")
                return

            episode_info = self._find_episode_info(absolute_episode)
            if not episode_info:
                self.logger.error(f"No episode info found for episode {absolute_episode}")
                return

            season_number = episode_info["season"]
            relative_episode = episode_info["episode_number"]

            if season_number == 0:
                season_dir = "Specjalne"
            else:
                season_dir = f"Sezon {season_number}"

            transcription_with_info = {
                "episode_info": episode_info,
                **transcription,
            }

            self._generate_full_json(transcription_with_info, season_dir, season_number, relative_episode)
            self._generate_segmented_json(transcription, season_dir, season_number, relative_episode)
            self._generate_simple_json(transcription, season_dir, season_number, relative_episode)
            self._generate_srt(transcription, season_dir, season_number, relative_episode)
            self._generate_txt(transcription, season_dir, season_number, relative_episode)

        except Exception as e:
            self.logger.error(f"Error processing file {transcription_file}: {e}")

    def _generate_full_json(self, data: dict, season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["json"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}.json"
        output_file = output_dir / filename

        generator = FullJsonGenerator(Path("."), output_dir, self.logger)
        full_json = generator._convert_to_full_format(data)
        full_json["episode_info"] = data.get("episode_info", {})

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(full_json, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Generated full JSON: {output_file}")

    def _generate_segmented_json(self, data: dict, season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["segmented_json"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}_segmented.json"
        output_file = output_dir / filename

        generator = SegmentedJsonGenerator(Path("."), output_dir, self.logger)
        segmented_json = generator._convert_to_segmented_format(data)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(segmented_json, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Generated segmented JSON: {output_file}")

    def _generate_simple_json(self, data: dict, season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["simple_json"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}_simple.json"
        output_file = output_dir / filename

        generator = SimpleJsonGenerator(Path("."), output_dir, self.logger)
        simple_json = generator._convert_to_simple_format(data)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(simple_json, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Generated simple JSON: {output_file}")

    def _generate_srt(self, data: dict, season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["srt"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}.srt"
        output_file = output_dir / filename

        generator = SrtGenerator(Path("."), output_dir, self.logger)
        srt_content = generator._convert_to_srt_format(data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(srt_content)

        self.logger.info(f"Generated SRT: {output_file}")

    def _generate_txt(self, data: dict, season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["txt"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}.txt"
        output_file = output_dir / filename

        generator = TxtGenerator(Path("."), output_dir, self.logger)
        txt_content = generator._convert_to_txt_format(data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(txt_content)

        self.logger.info(f"Generated TXT: {output_file}")

    def _find_episode_info(self, absolute_episode: int) -> Optional[dict]:
        for season in self.episodes_info.get("seasons", []):
            season_number = season["season_number"]
            episodes = sorted(season.get("episodes", []), key=lambda ep: ep["episode_number"])
            for idx, ep_data in enumerate(episodes):
                if ep_data.get("episode_number") == absolute_episode:
                    return {
                        "season": season_number,
                        "episode_number": idx + 1,
                        "premiere_date": ep_data["premiere_date"],
                        "title": ep_data["title"],
                        "viewership": ep_data["viewership"],
                    }
        return None

    @staticmethod
    def _get_episode_number(transcription_file: Path) -> Optional[int]:
        pattern = r"(?:E(?P<ep>\d+))|(?:_S\d{2}E(?P<ep2>\d+))"
        match = re.search(pattern, transcription_file.stem, re.IGNORECASE)
        if match:
            episode = match.group("ep") or match.group("ep2")
            return int(episode)
        return None
