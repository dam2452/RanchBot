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

from preprocessor.core.base_processor import BaseProcessor
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.transcription.engines.elevenlabs_engine import ElevenLabsEngine
from preprocessor.transcription.generators.multi_format_generator import MultiFormatGenerator
from preprocessor.utils.console import (
    console,
    create_progress,
)


class ElevenLabsTranscriber(BaseProcessor):
    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "videos" not in args:
            raise ValueError("videos is required")
        if "output_dir" not in args:
            raise ValueError("output_dir is required")
        if "series_name" not in args:
            raise ValueError("series_name is required")

        videos_path = Path(args["videos"])
        if not videos_path.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{videos_path}'")

    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=5,
            loglevel=logging.DEBUG,
        )

        self.input_videos: Path = Path(self._args["videos"])
        self.output_dir: Path = Path(self._args["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.episodes_info_json: Optional[Path] = self._args.get("episodes_info_json")

        self.model_id: str = self._args.get("model_id", "scribe_v1")
        self.language_code: str = self._args.get("language_code", "pol")
        self.diarize: bool = self._args.get("diarize", True)

        self.episode_manager = EpisodeManager(self.episodes_info_json, self.series_name)

        self.engine = ElevenLabsEngine(
            model_id=self.model_id,
            language_code=self.language_code,
            diarize=self.diarize,
        )

    def _execute(self) -> None:
        video_files: List[Path] = []
        for ext in self.SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(self.input_videos.rglob(f"*{ext}"))
        video_files = sorted(video_files)

        if not video_files:
            self.logger.warning("No video files found")
            return

        console.print(f"[blue]Found {len(video_files)} videos to transcribe with 11labs[/blue]")

        try:
            with create_progress() as progress:
                task = progress.add_task("Transcribing with 11labs...", total=len(video_files))

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

                    except Exception as e:
                        self.logger.error(f"Failed to transcribe {video_file.name}: {e}")

                    finally:
                        if audio_path and audio_path.exists():
                            audio_path.unlink()

                    progress.advance(task)
        except KeyboardInterrupt:
            console.print("\n[yellow]Transcription interrupted[/yellow]")
            raise

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
        episode_info = self.episode_manager.parse_filename(video_file)
        if not episode_info:
            self.logger.error(f"Cannot parse episode info from {video_file.name}")
            return

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
            "episode_info": EpisodeManager.get_metadata(episode_info),
        }

        json_dir = self.output_dir / "json"
        output_file = self.episode_manager.build_output_path(episode_info, json_dir)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Saved transcription: {output_file.name}")
