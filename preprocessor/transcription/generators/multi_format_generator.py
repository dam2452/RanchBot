import json
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.config.config import (
    get_base_output_dir,
    settings,
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

            filename = self.episode_manager.file_naming.build_filename(episode_info, extension="json")
            season_code = episode_info.season_code()
            episode_code = episode_info.episode_num()
            main_output_file = get_base_output_dir(self.series_name) / settings.output_subdirs.transcriptions / season_code / episode_code / "raw" / filename

            if main_output_file.exists():
                self.logger.info(f"Skipping (already exists): {episode_info.episode_code()}")
                return

            episode_metadata = EpisodeManager.get_metadata(episode_info)
            transcription_with_info = {
                "episode_info": episode_metadata,
                **transcription,
            }

            self.__generate_full_json(transcription_with_info, episode_info)
            self.__generate_segmented_json(transcription, episode_info)
            self.__generate_simple_json(transcription, episode_info)
            self.__generate_srt(transcription, episode_info)
            self.__generate_txt(transcription, episode_info)

        except Exception as e:
            self.logger.error(f"Error processing file {transcription_file}: {e}")

    def __generate_full_json(self, data: Dict[str, Any], episode_info) -> None:
        filename = self.episode_manager.file_naming.build_filename(episode_info, extension="json")
        season_code = episode_info.season_code()
        episode_code = episode_info.episode_num()
        output_file = get_base_output_dir(self.series_name) / settings.output_subdirs.transcriptions / season_code / episode_code / "raw" / filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        generator = FullJsonGenerator(Path("."), output_file.parent, self.logger)
        full_json = generator.convert_to_full_format(data)
        full_json["episode_info"] = data.get("episode_info", {})

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(full_json, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Generated full JSON: {output_file}")

    def __generate_segmented_json(self, data: Dict[str, Any], episode_info) -> None:
        filename = self.episode_manager.file_naming.build_filename(
            episode_info,
            extension="json",
            suffix="segmented",
        )
        season_code = episode_info.season_code()
        episode_code = episode_info.episode_num()
        output_file = get_base_output_dir(self.series_name) / settings.output_subdirs.transcriptions / season_code / episode_code / "raw" / filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        generator = SegmentedJsonGenerator(Path("."), output_file.parent, self.logger)
        segmented_json = generator.convert_to_segmented_format(data)

        segmented_json["episode_info"] = {
            "season": episode_info.season,
            "episode_number": episode_info.relative_episode,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(segmented_json, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Generated segmented JSON: {output_file}")

    def __generate_simple_json(self, data: Dict[str, Any], episode_info) -> None:
        filename = self.episode_manager.file_naming.build_filename(
            episode_info,
            extension="json",
            suffix="simple",
        )
        season_code = episode_info.season_code()
        episode_code = episode_info.episode_num()
        output_file = get_base_output_dir(self.series_name) / settings.output_subdirs.transcriptions / season_code / episode_code / "raw" / filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        generator = SimpleJsonGenerator(Path("."), output_file.parent, self.logger)
        simple_json = generator.convert_to_simple_format(data)

        simple_json["episode_info"] = {
            "season": episode_info.season,
            "episode_number": episode_info.relative_episode,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(simple_json, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Generated simple JSON: {output_file}")

    def __generate_srt(self, data: Dict[str, Any], episode_info) -> None:
        filename = self.episode_manager.file_naming.build_filename(episode_info, extension="srt")
        season_code = episode_info.season_code()
        episode_code = episode_info.episode_num()
        output_file = get_base_output_dir(self.series_name) / settings.output_subdirs.transcriptions / season_code / episode_code / "raw" / filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        generator = SrtGenerator(Path("."), output_file.parent, self.logger)
        srt_content = generator.convert_to_srt_format(data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(srt_content)

        self.logger.info(f"Generated SRT: {output_file}")

    def __generate_txt(self, data: Dict[str, Any], episode_info) -> None:
        filename = self.episode_manager.file_naming.build_filename(episode_info, extension="txt")
        season_code = episode_info.season_code()
        episode_code = episode_info.episode_num()
        output_file = get_base_output_dir(self.series_name) / settings.output_subdirs.transcriptions / season_code / episode_code / "raw" / filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        generator = TxtGenerator(Path("."), output_file.parent, self.logger)
        txt_content = generator.convert_to_txt_format(data)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(txt_content)

        self.logger.info(f"Generated TXT: {output_file}")
