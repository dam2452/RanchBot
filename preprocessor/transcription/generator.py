import logging
from pathlib import Path
import tempfile
from typing import (
    Any,
    Dict,
)

from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.transcription.generators.multi_format_generator import MultiFormatGenerator
from preprocessor.transcription.processors.audio_normalizer import AudioNormalizer
from preprocessor.transcription.processors.normalized_audio_processor import NormalizedAudioProcessor
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class TranscriptionGenerator:
    DEFAULT_OUTPUT_DIR: Path = Path("/app/output_data/transcriptions")
    DEFAULT_MODEL: str = "large-v3-turbo"
    DEFAULT_LANGUAGE: str = "Polish"
    DEFAULT_DEVICE: str = "cuda"

    def __init__(self, args: Dict[str, Any]) -> None:
        self.__input_videos: Path = Path(args["videos"])
        if not self.__input_videos.is_dir():
            raise NotADirectoryError(
                f"Input videos is not a directory: '{self.__input_videos}'",
            )

        ramdisk_path = args.get("ramdisk_path")
        if ramdisk_path and Path(ramdisk_path).exists():
            self.__temp_dir = tempfile.TemporaryDirectory(dir=str(ramdisk_path))
        else:
            self.__temp_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

        self.__logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=2,
        )

        self.__series_name: str = args.get("name", "unknown").lower()
        self.__episodes_info_json: Path = Path(args["episodes_info_json"])
        self.__episode_manager = EpisodeManager(self.__episodes_info_json, self.__series_name)

        self.__init_workers(args)

    def work(self) -> int:
        try:
            if self.__check_all_transcriptions_exist():
                self.__logger.info("All transcriptions already exist, skipping...")
                return self.__logger.finalize()

            self.__logger.info("Step 1/3: Normalizing audio from videos...")
            self.__audio_normalizer()

            self.__logger.info("Step 2/3: Generating transcriptions with Whisper...")
            self.__audio_processor()

            self.__logger.info("Cleaning up Whisper model...")
            self.__audio_processor.cleanup()

            self.__logger.info("Step 3/3: Generating multi-format output...")
            self.__multi_format_generator()

        except (RuntimeError, OSError, ValueError) as e:
            self.__logger.error(f"Error generating transcriptions: {e}")
        finally:
            self.__temp_dir.cleanup()

        return self.__logger.finalize()

    def __check_all_transcriptions_exist(self) -> bool:
        if not self.__episodes_info_json.exists():
            self.__logger.debug(f"Episodes info JSON not found: {self.__episodes_info_json}")
            return False

        video_files = list(self.__input_videos.rglob("*.mp4")) + list(self.__input_videos.rglob("*.mkv"))
        if not video_files:
            self.__logger.debug("No video files found to check")
            return False

        missing_files = []
        for video_file in video_files:
            episode_info = self.__episode_manager.parse_filename(video_file)
            if not episode_info:
                continue

            expected_file = self.__episode_manager.build_output_path(
                episode_info,
                self.__final_output_dir / "json",
                ".json",
            )

            if not expected_file.exists():
                missing_files.append(f"{video_file.name} -> {expected_file}")

        if missing_files:
            self.__logger.debug(f"Missing {len(missing_files)} transcription(s), first: {missing_files[0]}")
            return False

        self.__logger.info(f"All transcriptions already exist for {len(video_files)} video(s)")
        return True

    def __init_workers(self, args: Dict[str, Any]) -> None:
        temp_dir_path: Path = Path(self.__temp_dir.name) / "transcription_generator"
        normalizer_output: Path = temp_dir_path / "normalizer"
        processor_output: Path = temp_dir_path / "processor"

        self.__final_output_dir: Path = Path(args["transcription_jsons"])

        self.__audio_normalizer: AudioNormalizer = AudioNormalizer(
            input_videos=self.__input_videos,
            output_dir=normalizer_output,
            logger=self.__logger,
        )

        self.__audio_processor: NormalizedAudioProcessor = NormalizedAudioProcessor(
            input_audios=normalizer_output,
            output_dir=processor_output,
            logger=self.__logger,
            language=args["language"],
            model=args["model"],
            device=args["device"],
        )

        self.__multi_format_generator: MultiFormatGenerator = MultiFormatGenerator(
            jsons_dir=processor_output,
            episodes_info_json=self.__episodes_info_json,
            output_base_path=self.__final_output_dir,
            logger=self.__logger,
            series_name=args["name"],
        )
