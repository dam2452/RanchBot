import logging
import tempfile
from pathlib import Path
from typing import Dict

from preprocessor.transcriptions.audio_normalizer import AudioNormalizer
from preprocessor.transcriptions.episode_info_processor import EpisodeInfoProcessor
from preprocessor.transcriptions.json_generator import JsonGenerator
from preprocessor.transcriptions.normalized_audio_processor import NormalizedAudioProcessor
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class TranscriptionGenerator:
    DEFAULT_OUTPUT_DIR: Path = Path("transcriptions")
    DEFAULT_MODEL: str = "large-v3-turbo"
    DEFAULT_LANGUAGE: str = "Polish"
    DEFAULT_DEVICE: str = "cuda"

    def __init__(self, args: Dict):
        self.__input_videos: Path = Path(args["videos"])
        if not self.__input_videos.is_dir():
            raise NotADirectoryError(
                f"Input videos is not a directory: '{self.__input_videos}'"
            )

        self.__temp_dir: tempfile.TemporaryDirectory = (
            tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        )

        self.__logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=2,
        )

        self.__init_workers(args)

    def work(self) -> int:
        try:
            self.__logger.info("Step 1/4: Normalizing audio from videos...")
            self.__audio_normalizer()

            self.__logger.info("Step 2/4: Generating transcriptions with Whisper...")
            self.__audio_processor()

            self.__logger.info("Step 3/4: Processing transcription JSONs...")
            self.__json_generator()

            self.__logger.info("Step 4/4: Adding episode metadata...")
            self.__episode_info_processor()

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.__logger.error(f"Error generating transcriptions: {e}")

        return self.__logger.finalize()

    def __init_workers(self, args: Dict) -> None:
        temp_dir_path: Path = Path(self.__temp_dir.name) / "transcription_generator"
        normalizer_output = temp_dir_path / "normalizer"
        processor_output: Path = temp_dir_path / "processor"
        json_output: Path = temp_dir_path / "jsons"

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

        self.__json_generator: JsonGenerator = JsonGenerator(
            jsons_dir=processor_output,
            output_dir=json_output,
            logger=self.__logger,
            extra_keys_to_remove=args["extra_json_keys_to_remove"],
        )

        self.__episode_info_processor: EpisodeInfoProcessor = EpisodeInfoProcessor(
            jsons_dir=json_output,
            episodes_info_json=Path(args["episodes_info_json"]),
            output_path=Path(args["transcription_jsons"]),
            logger=self.__logger,
            series_name=args["name"],
        )
