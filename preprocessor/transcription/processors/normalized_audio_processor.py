import gc
import json
from pathlib import Path
from typing import (
    List,
    Optional,
    Tuple,
)

from faster_whisper import WhisperModel
import torch

from preprocessor.transcription.whisper_utils import (
    build_transcription_result,
    get_language_code,
)
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
        audio_files: Optional[List[Path]] = None,
    ):
        self.__input_audios: Path = input_audios
        self.__output_dir: Path = output_dir
        self.__logger: ErrorHandlingLogger = logger
        self.__audio_files: Optional[List[Path]] = audio_files

        self.__language: str = language

        self.__input_audios.mkdir(parents=True, exist_ok=True)
        self.__output_dir.mkdir(parents=True, exist_ok=True)

        if device != "cuda":
            raise ValueError(f"Only GPU (cuda) is supported, got device={device}")

        compute_type = "float16"
        self.__logger.info(f"Loading Whisper model {model} on {device} with compute_type={compute_type}")
        self.__whisper_model = WhisperModel(model, device=device, compute_type=compute_type)

    def __call__(self) -> None:
        if self.__audio_files is not None:
            for audio in self.__audio_files:
                self.__process_normalized_audio(audio)
        else:
            for audio in self.__input_audios.rglob("*"):
                if audio.suffix.lower() in self.SUPPORTED_AUDIO_EXTENSIONS:
                    self.__process_normalized_audio(audio)

    def __process_normalized_audio(self, normalized_audio: Path) -> None:
        try:
            output_file = self.__output_dir / normalized_audio.with_suffix(".json").name

            if output_file.exists():
                return

            language_code = get_language_code(self.__language)

            segments, info = self.__whisper_model.transcribe(
                str(normalized_audio),
                language=language_code,
                beam_size=10,
                word_timestamps=True,
                condition_on_previous_text=False,
                temperature=0.0,
                compression_ratio_threshold=None,
            )

            result = build_transcription_result(segments, language=info.language)

            for segment_dict in result["segments"]:
                segment_dict["temperature"] = 0.0

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.__logger.info(f"Processed: {normalized_audio}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.__logger.error(f"Error processing file {normalized_audio}: {e}")

    def cleanup(self) -> None:
        self.__logger.info("Unloading Whisper model and clearing GPU memory...")
        if hasattr(self, '_NormalizedAudioProcessor__whisper_model'):
            del self.__whisper_model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self.__logger.info("Whisper model unloaded, GPU memory cleared")
