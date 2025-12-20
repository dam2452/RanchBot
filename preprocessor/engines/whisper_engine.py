import gc
import logging
from pathlib import Path
from typing import Dict

from faster_whisper import WhisperModel
import torch

from preprocessor.engines.base_engine import TranscriptionEngine
from preprocessor.utils.console import console


class WhisperEngine(TranscriptionEngine):
    def __init__(
        self,
        model: str = "large-v3-turbo",
        language: str = "Polish",
        device: str = "cuda",
    ):
        self.model_name = model
        self.language = language
        self.device = device

        self.logger = logging.getLogger(self.__class__.__name__)

        if device != "cuda":
            raise ValueError(f"Only GPU (cuda) is supported, got device={device}")

        compute_type = "float16"
        console.print(f"[cyan]Loading Whisper model: {model} on {device} with compute_type={compute_type}[/cyan]")
        self.model = WhisperModel(model, device=device, compute_type=compute_type)
        console.print("[green]✓ Whisper model loaded[/green]")

    def transcribe(self, audio_path: Path) -> Dict:
        console.print(f"[cyan]Transcribing with Whisper: {audio_path.name}[/cyan]")

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        language_map = {
            "polish": "pl",
            "english": "en",
            "german": "de",
            "french": "fr",
            "spanish": "es",
        }
        language_code = language_map.get(self.language.lower(), self.language.lower())

        segments, info = self.model.transcribe(
            str(audio_path),
            language=language_code,
            beam_size=10,
            word_timestamps=True,
            condition_on_previous_text=False,
        )

        result = {
            "text": "",
            "segments": [],
            "language": info.language,
        }

        for segment in segments:
            words = []
            if hasattr(segment, 'words') and segment.words:
                for word in segment.words:
                    words.append({
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability,
                    })

            result["segments"].append({
                "id": segment.id,
                "seek": 0,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "tokens": [],
                "avg_logprob": segment.avg_logprob,
                "compression_ratio": segment.compression_ratio,
                "no_speech_prob": segment.no_speech_prob,
                "words": words,
            })
            result["text"] += segment.text

        console.print(f"[green]✓ Transcription completed: {audio_path.name}[/green]")

        return result

    def get_name(self) -> str:
        return f"Whisper-{self.model_name}"

    def cleanup(self) -> None:
        console.print("[cyan]Unloading Whisper model and clearing GPU memory...[/cyan]")
        if hasattr(self, 'model'):
            del self.model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        console.print("[green]✓ Whisper model unloaded, GPU memory cleared[/green]")
