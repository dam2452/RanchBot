import json
from pathlib import Path

from preprocessor.transcriptions.generators.full_json_generator import FullJsonGenerator
from preprocessor.transcriptions.generators.segmented_json_generator import SegmentedJsonGenerator
from preprocessor.transcriptions.generators.simple_json_generator import SimpleJsonGenerator
from preprocessor.transcriptions.generators.srt_generator import SrtGenerator
from preprocessor.transcriptions.generators.txt_generator import TxtGenerator
from preprocessor.utils.episode_utils import (
    extract_episode_number,
    find_episode_info_by_absolute,
)
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


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
            self.__process_file(transcription_file)

    def __process_file(self, transcription_file: Path) -> None:
        try:  # pylint: disable=too-many-try-statements
            with open(transcription_file, "r", encoding="utf-8") as f:
                transcription = json.load(f)

            absolute_episode = extract_episode_number(transcription_file)
            if absolute_episode is None:
                self.logger.error(f"Cannot extract episode number from {transcription_file.name}")
                return

            episode_info = find_episode_info_by_absolute(self.episodes_info, absolute_episode)
            if not episode_info:
                self.logger.error(f"No episode info found for episode {absolute_episode}")
                return

            season_number = episode_info["season"]
            relative_episode = episode_info["episode_number"]

            if season_number == 0:
                season_dir = "Specjalne"
            else:
                season_dir = f"Sezon {season_number}"

            output_filename = f"{self.series_name}_S{season_number:02d}E{relative_episode:02d}.json"
            main_output_file = self.format_dirs["json"] / season_dir / output_filename

            if main_output_file.exists():
                self.logger.info(f"Skipping (already exists): {output_filename}")
                return

            transcription_with_info = {
                "episode_info": episode_info,
                **transcription,
            }

            self.__generate_full_json(transcription_with_info, season_dir, season_number, relative_episode)
            self.__generate_segmented_json(transcription, season_dir, season_number, relative_episode)
            self.__generate_simple_json(transcription, season_dir, season_number, relative_episode)
            self.__generate_srt(transcription, season_dir, season_number, relative_episode)
            self.__generate_txt(transcription, season_dir, season_number, relative_episode)

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Error processing file {transcription_file}: {e}")

    def __generate_full_json(self, data: dict, season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["json"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}.json"
        output_file = output_dir / filename

        generator = FullJsonGenerator(Path("."), output_dir, self.logger)
        full_json = generator.convert_to_full_format(data)
        full_json["episode_info"] = data.get("episode_info", {})

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(full_json, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Generated full JSON: {output_file}")

    def __generate_segmented_json(self, data: dict, season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["segmented_json"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}_segmented.json"
        output_file = output_dir / filename

        generator = SegmentedJsonGenerator(Path("."), output_dir, self.logger)
        segmented_json = generator.convert_to_segmented_format(data)

        segmented_json["episode_info"] = {
            "season": season,
            "episode_number": episode,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(segmented_json, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Generated segmented JSON: {output_file}")

    def __generate_simple_json(self, data: dict, season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["simple_json"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}_simple.json"
        output_file = output_dir / filename

        generator = SimpleJsonGenerator(Path("."), output_dir, self.logger)
        simple_json = generator.convert_to_simple_format(data)

        simple_json["episode_info"] = {
            "season": season,
            "episode_number": episode,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(simple_json, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Generated simple JSON: {output_file}")

    def __generate_srt(self, data: dict, season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["srt"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}.srt"
        output_file = output_dir / filename

        generator = SrtGenerator(Path("."), output_dir, self.logger)
        srt_content = generator.convert_to_srt_format(data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(srt_content)

        self.logger.info(f"Generated SRT: {output_file}")

    def __generate_txt(self, data: dict, season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["txt"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}.txt"
        output_file = output_dir / filename

        generator = TxtGenerator(Path("."), output_dir, self.logger)
        txt_content = generator.convert_to_txt_format(data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(txt_content)

        self.logger.info(f"Generated TXT: {output_file}")
