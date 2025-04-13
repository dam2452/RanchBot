import json
import logging
from pathlib import Path
import tempfile

from preprocessor.transcriptions import *  # pylint: disable=wildcard-import
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class TranscriptionGenerator:
    DEFAULT_OUTPUT_DIR: Path = "transcriptions"
    DEFAULT_MODEL: str = "large-v3-turbo"
    DEFAULT_LANGUAGE: str = "Polish"
    DEFAULT_DEVICE: str = "cuda"

    def __init__(self, args: json):
        self.__input_videos: Path = Path(args["videos"])
        if not self.__input_videos.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{self.__input_videos}'")

        self.__temp_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

        self.__logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=2,
        )

        self.__init__workers(args)

    def work(self) -> int:
        try:
            self.__audio_normalizer()
            self.__audio_processor()
            self.__json_generator()
            self.__episode_info_processor()
        except Exception as e: # pylint: disable=broad-exception-caught
            self.__logger.error(f"Error generating transcriptions: {e}")

        return self.__logger.finalize()

    def __init__workers(self, args: json) -> None:
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
