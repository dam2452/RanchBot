import json
import logging
from pathlib import Path
import subprocess
import tempfile
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from rich.console import Console
from rich.progress import Progress

from preprocessor.core.state_manager import StateManager
from preprocessor.engines.elevenlabs_engine import ElevenLabsEngine
from preprocessor.transcriptions.generators.multi_format_generator import MultiFormatGenerator
from preprocessor.utils.episode_utils import (
    build_output_path,
    extract_season_episode_from_filename,
    get_episode_metadata,
)
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger

console = Console()


class ElevenLabsTranscriber:
    def __init__(self, args: Dict[str, Any]):
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
                        audio_path = self.__extract_audio(video_file)
                        self.state_manager.mark_step_started("transcribe_11labs", episode_id, [str(audio_path)])

                    audio_path = audio_path or self.__extract_audio(video_file)
                    transcription_data = self.engine.transcribe(audio_path)

                    self.__save_transcription(transcription_data, video_file)

                    if self.state_manager:
                        self.state_manager.mark_step_completed("transcribe_11labs", episode_id)

                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.error(f"Failed to transcribe {video_file.name}: {e}")

                finally:
                    if audio_path and audio_path.exists():
                        audio_path.unlink()

                progress.advance(task)

        console.print("[blue]Generating multi-format outputs (SRT, TXT, etc.)...[/blue]")
        if self.episodes_info_json:
            jsons_source_dir = self.output_dir / "json"
            multi_format_gen = MultiFormatGenerator(
                jsons_dir=jsons_source_dir,
                episodes_info_json=self.episodes_info_json,
                output_base_path=self.output_dir,
                logger=self.logger,
                series_name=self.series_name,
            )
            multi_format_gen.generate()

        return self.logger.finalize()

    @staticmethod
    def __create_segments_from_words(words: List[Dict]) -> List[Dict]:
        if not words:
            return []

        segments = []
        current_segment_words = []
        current_speaker = None

        for word in words:
            speaker_id = word.get("speaker_id", "speaker_unknown")

            if current_speaker is None:
                current_speaker = speaker_id
                current_segment_words = [word]
            elif speaker_id == current_speaker:
                current_segment_words.append(word)
            else:
                segment_text = " ".join(w.get("text", "") for w in current_segment_words).strip()
                segments.append({
                    "text": segment_text,
                    "words": current_segment_words,
                })
                current_speaker = speaker_id
                current_segment_words = [word]

        if current_segment_words:
            segment_text = " ".join(w.get("text", "") for w in current_segment_words).strip()
            segments.append({
                "text": segment_text,
                "words": current_segment_words,
            })

        return segments

    @staticmethod
    def __extract_audio(video_file: Path) -> Path:
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

    def __save_transcription(self, data: Dict[str, Any], video_file: Path) -> None:
        season, episode = extract_season_episode_from_filename(video_file)
        episode_info = get_episode_metadata(self.episodes_info, season, episode)

        api_segments = data.get("segments", [])
        api_words = data.get("words", [])

        if api_segments:
            segments = api_segments
            words = []
            for segment in segments:
                segment_words = segment.get("words", [])
                for word in segment_words:
                    if "speaker_id" not in word and "speaker" in segment:
                        word["speaker_id"] = segment["speaker"]
                words.extend(segment_words)
        else:
            words = api_words
            segments = self.__create_segments_from_words(words)

        output_data = {
            "text": data.get("text", ""),
            "language_code": data.get("language_code", "pol"),
            "segments": segments,
            "words": words,
        }

        if episode_info:
            # noinspection PyTypeChecker
            output_data["episode_info"] = episode_info

        json_dir = self.output_dir / "json"
        output_file = build_output_path(json_dir, self.series_name, season, episode)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Saved transcription: {output_file.name}")
