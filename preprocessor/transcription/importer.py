import json
import logging
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from preprocessor.core.base_processor import BaseProcessor
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.utils.console import (
    console,
    create_progress,
)


class TranscriptionImporter(BaseProcessor):
    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "source_dir" not in args:
            raise ValueError("source_dir is required")
        if "output_dir" not in args:
            raise ValueError("output_dir is required")
        if "series_name" not in args:
            raise ValueError("series_name is required")

        source_dir = Path(args["source_dir"])
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=4,
            loglevel=logging.DEBUG,
        )

        self.source_dir: Path = Path(self._args["source_dir"])
        self.output_dir: Path = Path(self._args["output_dir"])
        self.episodes_info_json: Optional[Path] = self._args.get("episodes_info_json")
        self.format_type: str = self._args.get("format_type", "11labs_segmented")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.episode_manager = EpisodeManager(self.episodes_info_json, self.series_name)

    def _execute(self) -> None:
        json_files = self.__find_transcription_files()

        if not json_files:
            self.logger.warning(f"No transcription files found in {self.source_dir}")
            return

        console.print(f"[blue]Found {len(json_files)} transcription files to import[/blue]")

        try:
            with create_progress() as progress:
                task = progress.add_task("Importing transcriptions...", total=len(json_files))

                for json_file in json_files:
                    episode_id = self.__extract_episode_id(json_file)

                    if self.state_manager and self.state_manager.is_step_completed("import", episode_id):
                        console.print(f"[yellow]Skipping (already imported): {episode_id}[/yellow]")
                        progress.advance(task)
                        continue

                    if self.state_manager:
                        self.state_manager.mark_step_started("import", episode_id)

                    try:
                        self.__import_single_file(json_file)
                        if self.state_manager:
                            self.state_manager.mark_step_completed("import", episode_id)
                    except Exception as e:
                        self.logger.error(f"Failed to import {json_file.name}: {e}")

                    progress.advance(task)
        except KeyboardInterrupt:
            console.print("\n[yellow]Import interrupted[/yellow]")
            raise

    def __find_transcription_files(self) -> List[Path]:
        if self.format_type == "11labs_segmented":
            pattern = "*_segmented.json"
        elif self.format_type == "11labs":
            pattern = "*.json"
        else:
            pattern = "*.json"

        files = sorted(self.source_dir.rglob(pattern))
        files = [f for f in files if not f.name.startswith('.')]

        return files

    @staticmethod
    def __extract_episode_id(file_path: Path) -> str:
        match = re.search(r'S(\d+)E(\d+)', file_path.name, re.IGNORECASE)
        if match:
            return f"S{match.group(1)}E{match.group(2)}"

        match = re.search(r'E(\d+)', file_path.stem, re.IGNORECASE)
        if match:
            return f"E{match.group(1)}"

        return file_path.stem

    def __import_single_file(self, json_file: Path) -> None:
        with open(json_file, "r", encoding="utf-8") as f:
            source_data = json.load(f)

        if self.format_type == "11labs_segmented":
            converted_data = self.__convert_11labs_segmented(source_data, json_file)
        elif self.format_type == "11labs":
            converted_data = self.__convert_11labs_full(source_data, json_file)
        else:
            self.logger.error(f"Unknown format type: {self.format_type}")
            return

        episode_info = self.episode_manager.parse_filename(json_file)
        if not episode_info:
            season_num, episode_num = self.__extract_season_episode_fallback(json_file)
            episode_info = self.episode_manager.get_episode_by_season_and_relative(season_num, episode_num)

        if episode_info:
            converted_data["episode_info"] = EpisodeManager.get_metadata(episode_info)

        output_file = self.episode_manager.build_output_path(episode_info, self.output_dir)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(converted_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Imported: {json_file.name} -> {output_file.name}")

    @staticmethod
    def __convert_11labs_segmented(data: Dict[str, Any], source_file: Path) -> Dict[str, Any]:
        segments = []

        for i, segment in enumerate(data.get("segments", [])):
            converted_segment = {
                "id": i,
                "start": segment.get("start"),
                "end": segment.get("end"),
                "text": segment.get("text", ""),
                "speaker": segment.get("speaker", "unknown"),
                "words": segment.get("words", []),
            }
            segments.append(converted_segment)

        return {
            "transcription": {
                "format": "11labs_segmented",
                "source_file": source_file.name,
                "segments": segments,
            },
            "segments": segments,
        }

    @staticmethod
    def __convert_11labs_full(data: Dict[str, Any], source_file: Path) -> Dict[str, Any]:
        segments = []
        words = data.get("words", [])

        current_segment = {
            "words": [],
            "start": None,
            "end": None,
            "text": "",
            "speaker": "unknown",
        }

        for word in words:
            if current_segment["start"] is None:
                current_segment["start"] = word.get("start")

            current_segment["words"].append(word)
            current_segment["end"] = word.get("end")

            if word.get("text", "").endswith((".", "!", "?")) or len(current_segment["words"]) >= 20:
                current_segment["text"] = " ".join(w.get("text", "") for w in current_segment["words"])
                segments.append(dict(current_segment))
                current_segment = {
                    "words": [],
                    "start": None,
                    "end": None,
                    "text": "",
                    "speaker": word.get("speaker_id", "unknown"),
                }

        if current_segment["words"]:
            current_segment["text"] = " ".join(w.get("text", "") for w in current_segment["words"])
            segments.append(current_segment)

        for i, seg in enumerate(segments):
            seg["id"] = i

        return {
            "transcription": {
                "format": "11labs",
                "source_file": source_file.name,
                "language_code": data.get("language_code", "pol"),
                "language_probability": data.get("language_probability", 1.0),
            },
            "segments": segments,
        }

    @staticmethod
    def __extract_season_episode_fallback(file_path: Path) -> Tuple[int, int]:
        match = re.search(r'S(\d+)E(\d+)', file_path.name, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))

        parent_match = re.search(r'S(\d+)', file_path.parent.name, re.IGNORECASE)
        if parent_match:
            season = int(parent_match.group(1))
            episode_match = re.search(r'E(\d+)', file_path.name, re.IGNORECASE)
            if episode_match:
                return season, int(episode_match.group(1))

        return 1, 1
