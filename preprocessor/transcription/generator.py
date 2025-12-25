import logging
from pathlib import Path
import tempfile
from typing import (
    Any,
    Dict,
)

from preprocessor.core.base_processor import BaseProcessor
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.transcription.generators.multi_format_generator import MultiFormatGenerator
from preprocessor.transcription.processors.audio_normalizer import AudioNormalizer
from preprocessor.transcription.processors.normalized_audio_processor import NormalizedAudioProcessor


class TranscriptionGenerator(BaseProcessor):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=2,
            loglevel=logging.DEBUG,
        )

        self.input_videos: Path = Path(self._args["videos"])
        ramdisk_path = self._args.get("ramdisk_path")
        if ramdisk_path and Path(ramdisk_path).exists():
            self.temp_dir = tempfile.TemporaryDirectory(dir=str(ramdisk_path))
        else:
            self.temp_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

        self.series_name_lower: str = self._args.get("name", "unknown").lower()
        self.episodes_info_json: Path = Path(self._args["episodes_info_json"])
        self.episode_manager = EpisodeManager(self.episodes_info_json, self.series_name_lower)

        self._init_workers(self._args)

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "videos" not in args:
            raise ValueError("videos path is required")
        if "episodes_info_json" not in args:
            raise ValueError("episodes_info_json is required")

        videos_path = Path(args["videos"])
        if not videos_path.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{videos_path}'")

    def _execute(self) -> None:
        try:
            if self._check_all_transcriptions_exist():
                self.logger.info("All transcriptions already exist, skipping...")
                return

            self.logger.info("Step 1/3: Normalizing audio from videos...")
            self.audio_normalizer()

            self.logger.info("Step 2/3: Generating transcriptions with Whisper...")
            self.audio_processor()

            self.logger.info("Cleaning up Whisper model...")
            self.audio_processor.cleanup()

            self.logger.info("Step 3/3: Generating multi-format output...")
            self.multi_format_generator()

        except (RuntimeError, OSError, ValueError) as e:
            self.logger.error(f"Error generating transcriptions: {e}")
        finally:
            self.temp_dir.cleanup()

    def _check_all_transcriptions_exist(self) -> bool:
        if not self.episodes_info_json.exists():
            self.logger.debug(f"Episodes info JSON not found: {self.episodes_info_json}")
            return False

        video_files = list(self.input_videos.rglob("*.mp4")) + list(self.input_videos.rglob("*.mkv"))
        if not video_files:
            self.logger.debug("No video files found to check")
            return False

        missing_files = []
        for video_file in video_files:
            episode_info = self.episode_manager.parse_filename(video_file)
            if not episode_info:
                continue

            expected_file = self.episode_manager.build_output_path(
                episode_info,
                self.final_output_dir / "json",
                ".json",
            )

            if not expected_file.exists():
                missing_files.append(f"{video_file.name} -> {expected_file}")

        if missing_files:
            self.logger.debug(f"Missing {len(missing_files)} transcription(s), first: {missing_files[0]}")
            return False

        self.logger.info(f"All transcriptions already exist for {len(video_files)} video(s)")
        return True

    def _init_workers(self, args: Dict[str, Any]) -> None:
        temp_dir_path: Path = Path(self.temp_dir.name) / "transcription_generator"
        normalizer_output: Path = temp_dir_path / "normalizer"
        processor_output: Path = temp_dir_path / "processor"

        self.final_output_dir: Path = Path(args["transcription_jsons"])

        self.audio_normalizer: AudioNormalizer = AudioNormalizer(
            input_videos=self.input_videos,
            output_dir=normalizer_output,
            logger=self.logger,
        )

        self.audio_processor: NormalizedAudioProcessor = NormalizedAudioProcessor(
            input_audios=normalizer_output,
            output_dir=processor_output,
            logger=self.logger,
            language=args["language"],
            model=args["model"],
            device=args["device"],
        )

        self.multi_format_generator: MultiFormatGenerator = MultiFormatGenerator(
            jsons_dir=processor_output,
            episodes_info_json=self.episodes_info_json,
            output_base_path=self.final_output_dir,
            logger=self.logger,
            series_name=args["name"],
        )
