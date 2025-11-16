import logging
from pathlib import Path
from typing import Dict

from rich.console import Console
import whisper

from preprocessor.engines.base_engine import TranscriptionEngine

console = Console()


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

        console.print(f"[cyan]Loading Whisper model: {model} on {device}[/cyan]")
        self.model = whisper.load_model(model, device=device)
        console.print("[green]✓ Whisper model loaded[/green]")

    def transcribe(self, audio_path: Path) -> Dict:
        console.print(f"[cyan]Transcribing with Whisper: {audio_path.name}[/cyan]")

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # noinspection PyArgumentList
        result = self.model.transcribe(  # type: ignore[call-arg]
            audio=str(audio_path),
            language=self.language,
            verbose=False,
        )

        console.print(f"[green]✓ Transcription completed: {audio_path.name}[/green]")

        return result

    def get_name(self) -> str:
        return f"Whisper-{self.model_name}"
