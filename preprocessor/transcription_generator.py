import logging
from pathlib import Path
import tempfile
from typing import (
    Dict,
    Optional,
)

from rich.console import Console

from preprocessor.state_manager import StateManager
from preprocessor.transcriptions.audio_normalizer import AudioNormalizer
from preprocessor.transcriptions.multi_format_generator import MultiFormatGenerator
from preprocessor.transcriptions.normalized_audio_processor import NormalizedAudioProcessor
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger

console = Console()


class TranscriptionGenerator:
    DEFAULT_OUTPUT_DIR: Path = Path("transcriptions")
    DEFAULT_MODEL: str = "large-v3-turbo"
    DEFAULT_LANGUAGE: str = "Polish"
    DEFAULT_DEVICE: str = "cuda"

    def __init__(self, args: Dict):
        self.__input_videos: Path = Path(args["videos"])
        if not self.__input_videos.is_dir():
            raise NotADirectoryError(
                f"Input videos is not a directory: '{self.__input_videos}'",
            )

        self.__temp_dir: tempfile.TemporaryDirectory = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )

        self.__logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=2,
        )

        self.state_manager: Optional[StateManager] = args.get("state_manager")
        self.series_name: str = args.get("series_name", "unknown")

        self.__init_workers(args)

    def work(self) -> int:
        try:
            self.__logger.info("Step 1/3: Normalizing audio from videos...")
            self.__audio_normalizer()

            self.__logger.info("Step 2/3: Generating transcriptions with Whisper...")
            self.__audio_processor()

            self.__logger.info("Step 3/3: Generating multi-format output...")
            self.__multi_format_generator()

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.__logger.error(f"Error generating transcriptions: {e}")

        return self.__logger.finalize()

    def __init_workers(self, args: Dict) -> None:
        temp_dir_path: Path = Path(self.__temp_dir.name) / "transcription_generator"
        normalizer_output = temp_dir_path / "normalizer"
        processor_output: Path = temp_dir_path / "processor"

        max_workers = args.get("max_workers", 1)

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
            episodes_info_json=Path(args["episodes_info_json"]),
            output_base_path=Path(args["transcription_jsons"]),
            logger=self.__logger,
            series_name=args["name"],
        )
