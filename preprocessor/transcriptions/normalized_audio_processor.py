from pathlib import Path
import subprocess
from typing import Tuple

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class NormalizedAudioProcessor:
    SUPPORTED_AUDIO_EXTENSIONS: Tuple[str, str] = (".wav", ".mp3")

    def __init__(
        self,
        input_audios: Path,
        output_dir: Path,
        logger: ErrorHandlingLogger,
        language: str,
        model: str,
        device: str,
    ):
        self.__input_audios: Path = input_audios
        self.__output_dir: Path = output_dir
        self.__logger: ErrorHandlingLogger = logger

        self.__language: str = language
        self.__model: str = model
        self.__device: str = device

        self.__input_audios.mkdir(parents=True, exist_ok=True)

    def __call__(self) -> None:
        for audio in self.__input_audios.rglob("*"):
            if audio.suffix.lower() in self.SUPPORTED_AUDIO_EXTENSIONS:
                self.__process_normalized_audio(audio)

    def __process_normalized_audio(self, normalized_audio: Path) -> None:
        try:
            subprocess.run(
                [
                    "whisper", str(normalized_audio),
                    "--model", self.__model,
                    "--language", self.__language,
                    "--device", self.__device,
                    "--output_dir", str(self.__output_dir),
                ],
                check=True,
            )
            self.__logger.info(f"Processed: {normalized_audio}")
        except Exception as e: # pylint: disable=broad-exception-caught
            self.__logger.error(f"Error processing file {normalized_audio}: {e}")
