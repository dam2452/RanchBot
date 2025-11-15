from pathlib import Path
import json
from typing import Tuple

from faster_whisper import WhisperModel

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
        self.__output_dir.mkdir(parents=True, exist_ok=True)

        compute_type = "float16" if device == "cuda" else "int8"
        self.__logger.info(f"Loading Whisper model {model} on {device} with compute_type={compute_type}")
        self.__whisper_model = WhisperModel(model, device=device, compute_type=compute_type)

    def __call__(self) -> None:
        for audio in self.__input_audios.rglob("*"):
            if audio.suffix.lower() in self.SUPPORTED_AUDIO_EXTENSIONS:
                self.__process_normalized_audio(audio)

    def __process_normalized_audio(self, normalized_audio: Path) -> None:
        try:
            language_map = {
                "polish": "pl",
                "english": "en",
                "german": "de",
                "french": "fr",
                "spanish": "es",
            }
            language_code = language_map.get(self.__language.lower(), self.__language)

            segments, info = self.__whisper_model.transcribe(
                str(normalized_audio),
                language=language_code,
                beam_size=5,
            )

            result = {
                "text": "",
                "segments": []
            }

            for segment in segments:
                result["segments"].append({
                    "id": segment.id,
                    "seek": 0,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "tokens": [],
                    "temperature": 0.0,
                    "avg_logprob": segment.avg_logprob,
                    "compression_ratio": segment.compression_ratio,
                    "no_speech_prob": segment.no_speech_prob,
                })
                result["text"] += segment.text

            result["language"] = info.language

            output_file = self.__output_dir / normalized_audio.with_suffix(".json").name
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            self.__logger.info(f"Processed: {normalized_audio}")
        except Exception as e:
            self.__logger.error(f"Error processing file {normalized_audio}: {e}")
