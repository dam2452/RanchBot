import json
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.transcription.generators.full_json_generator import FullJsonGenerator
from preprocessor.transcription.generators.segmented_json_generator import SegmentedJsonGenerator
from preprocessor.transcription.generators.simple_json_generator import SimpleJsonGenerator
from preprocessor.transcription.generators.srt_generator import SrtGenerator
from preprocessor.transcription.generators.txt_generator import TxtGenerator
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
        self.output_base_path = output_base_path
        self.logger = logger
        self.series_name = series_name.lower() if series_name else "unknown"

        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

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

            episode_info = self.episode_manager.parse_filename(transcription_file)
            if not episode_info:
                self.logger.error(f"Cannot extract episode info from {transcription_file.name}")
                return

            season_dir = episode_info.season_dir_name()
            output_filename = f"{self.series_name}_{episode_info.episode_code()}.json"
            main_output_file = self.format_dirs["json"] / season_dir / output_filename

            if main_output_file.exists():
                self.logger.info(f"Skipping (already exists): {output_filename}")
                return

            episode_metadata = EpisodeManager.get_metadata(episode_info)
            transcription_with_info = {
                "episode_info": episode_metadata,
                **transcription,
            }

            self.__generate_full_json(transcription_with_info, season_dir, episode_info.season, episode_info.relative_episode)
            self.__generate_segmented_json(transcription, season_dir, episode_info.season, episode_info.relative_episode)
            self.__generate_simple_json(transcription, season_dir, episode_info.season, episode_info.relative_episode)
            self.__generate_srt(transcription, season_dir, episode_info.season, episode_info.relative_episode)
            self.__generate_txt(transcription, season_dir, episode_info.season, episode_info.relative_episode)

        except Exception as e:
            self.logger.error(f"Error processing file {transcription_file}: {e}")

    def __generate_full_json(self, data: Dict[str, Any], season_dir: str, season: int, episode: int) -> None:
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

    def __generate_segmented_json(self, data: Dict[str, Any], season_dir: str, season: int, episode: int) -> None:
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

    def __generate_simple_json(self, data: Dict[str, Any], season_dir: str, season: int, episode: int) -> None:
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

    def __generate_srt(self, data: Dict[str, Any], season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["srt"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}.srt"
        output_file = output_dir / filename

        generator = SrtGenerator(Path("."), output_dir, self.logger)
        srt_content = generator.convert_to_srt_format(data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(srt_content)

        self.logger.info(f"Generated SRT: {output_file}")

    def __generate_txt(self, data: Dict[str, Any], season_dir: str, season: int, episode: int) -> None:
        output_dir = self.format_dirs["txt"] / season_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.series_name}_S{season:02d}E{episode:02d}.txt"
        output_file = output_dir / filename

        generator = TxtGenerator(Path("."), output_dir, self.logger)
        txt_content = generator.convert_to_txt_format(data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(txt_content)

        self.logger.info(f"Generated TXT: {output_file}")
