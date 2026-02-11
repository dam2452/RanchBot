from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
)

from faster_whisper import WhisperModel
import torch

from preprocessor.services.transcription.utils import WhisperUtils
from preprocessor.services.ui.console import console


class Whisper:

    def __init__(self, model: str='large-v3-turbo', language: str='pl', device: str='cuda', beam_size: int=10, temperature: float=0.0) -> None:
        self.model_name: str = model
        self.language: str = language
        self.device: str = device
        self.beam_size: int = beam_size
        self.temperature: float = temperature
        self._model: Optional[WhisperModel] = None

    def cleanup(self) -> None:
        console.print('[cyan]Unloading Whisper model and clearing GPU memory...[/cyan]')
        if self._model is not None:
            del self._model
            self._model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        console.print('[green]✓ Whisper model unloaded, GPU memory cleared[/green]')

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        console.print(f'[cyan]Transcribing with Whisper: {audio_path.name}[/cyan]')
        if not audio_path.exists():
            raise FileNotFoundError(f'Audio file not found: {audio_path}')
        model = self._load_model()
        language_code = WhisperUtils.get_language_code(self.language)
        segments, info = model.transcribe(
            str(audio_path),
            language=language_code,
            beam_size=self.beam_size,
            word_timestamps=True,
            condition_on_previous_text=False,
            temperature=self.temperature,
        )
        result = WhisperUtils.build_transcription_result(segments, language=info.language)
        console.print(f'[green]✓ Transcription completed: {audio_path.name}[/green]')
        return result

    def _load_model(self) -> WhisperModel:
        if self._model is not None:
            return self._model
        if self.device != 'cuda':
            raise ValueError(f'Only GPU (cuda) is supported, got device={self.device}')
        compute_type = 'float16'
        console.print(f'[cyan]Loading Whisper model: {self.model_name} on {self.device} with compute_type={compute_type}[/cyan]')
        self._model = WhisperModel(self.model_name, device=self.device, compute_type=compute_type)
        console.print('[green]✓ Whisper model loaded[/green]')
        return self._model
