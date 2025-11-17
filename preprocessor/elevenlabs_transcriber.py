import json
import logging
from pathlib import Path
import subprocess
import tempfile
from typing import (
    Dict,
    List,
    Optional,
)

from rich.console import Console
from rich.progress import Progress

from preprocessor.engines.elevenlabs_engine import ElevenLabsEngine
from preprocessor.state_manager import StateManager
from preprocessor.utils.episode_utils import (
    build_output_path,
    extract_season_episode_from_filename,
    get_episode_metadata,
)
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger

console = Console()


class ElevenLabsTranscriber:
    def __init__(self, args: Dict):
        self.input_videos: Path = Path(args["videos"])
        if not self.input_videos.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{self.input_videos}'")

        self.output_dir: Path = Path(args["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.episodes_info_json: Optional[Path] = args.get("episodes_info_json")
        self.series_name: str = args["series_name"]

        self.api_key: Optional[str] = args.get("api_key")
        self.model_id: str = args.get("model_id", "scribe_v1")
        self.language_code: str = args.get("language_code", "pol")
        self.diarize: bool = args.get("diarize", True)

        self.logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=5,
        )

        self.state_manager: Optional[StateManager] = args.get("state_manager")

        self.episodes_info: Optional[Dict] = None
        if self.episodes_info_json and self.episodes_info_json.exists():
            with open(self.episodes_info_json, "r", encoding="utf-8") as f:
                self.episodes_info = json.load(f)

        self.engine = ElevenLabsEngine(
            api_key=self.api_key,
            model_id=self.model_id,
            language_code=self.language_code,
            diarize=self.diarize,
        )

    def work(self) -> int:
        video_files: List[Path] = sorted(self.input_videos.rglob("*.mp4"))

        if not video_files:
            self.logger.warning("No video files found")
            return self.logger.finalize()

        console.print(f"[blue]Found {len(video_files)} videos to transcribe with 11labs[/blue]")

        with Progress() as progress:
            task = progress.add_task("[cyan]Transcribing with 11labs...", total=len(video_files))

            for video_file in video_files:
                episode_id = video_file.stem

                if self.state_manager and self.state_manager.is_step_completed("transcribe_11labs", episode_id):
                    console.print(f"[yellow]Skipping (already done): {episode_id}[/yellow]")
                    progress.advance(task)
                    continue

                audio_path = None
                try:
                    if self.state_manager:
                        audio_path = self._extract_audio(video_file)
                        self.state_manager.mark_step_started("transcribe_11labs", episode_id, [str(audio_path)])

                    audio_path = audio_path or self._extract_audio(video_file)
                    transcription_data = self.engine.transcribe(audio_path)

                    self._save_transcription(transcription_data, video_file)

                    if self.state_manager:
                        self.state_manager.mark_step_completed("transcribe_11labs", episode_id)

                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.error(f"Failed to transcribe {video_file.name}: {e}")

                finally:
                    if audio_path and audio_path.exists():
                        audio_path.unlink()

                progress.advance(task)

        return self.logger.finalize()

    @staticmethod
    def _extract_audio(video_file: Path) -> Path:
        temp_dir = Path(tempfile.gettempdir())
        audio_path = temp_dir / f"{video_file.stem}_audio.mp3"

        command = [
            "ffmpeg",
            "-v", "error",
            "-hide_banner",
            "-y",
            "-i", str(video_file),
            "-vn",
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            str(audio_path),
        ]

        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return audio_path

    def _save_transcription(self, data: Dict, video_file: Path) -> None:
        season, episode = extract_season_episode_from_filename(video_file)
        episode_info = get_episode_metadata(self.episodes_info, season, episode)

        output_data = {
            "transcription": data,
            "segments": data.get("segments", []),
        }

        if episode_info:
            output_data["episode_info"] = episode_info

        output_file = build_output_path(self.output_dir, self.series_name, season, episode)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Saved transcription: {output_file.name}")
