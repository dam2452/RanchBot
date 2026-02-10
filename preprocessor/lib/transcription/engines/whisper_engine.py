import gc
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from faster_whisper import WhisperModel
import torch

from preprocessor.lib.transcription.engines.base_engine import TranscriptionEngine
from preprocessor.lib.transcription.whisper import WhisperUtils
from preprocessor.lib.ui.console import console


class WhisperEngine(TranscriptionEngine):

    def __init__(self, model: str='large-v3-turbo', language: str='Polish', device: str='cuda'):
        self.model_name = model
        self.language = language
        self.device = device
        if device != 'cuda':
            raise ValueError(f'Only GPU (cuda) is supported, got device={device}')
        compute_type = 'float16'
        console.print(f'[cyan]Loading Whisper model: {model} on {device} with compute_type={compute_type}[/cyan]')
        self.model = WhisperModel(model, device=device, compute_type=compute_type)
        console.print('[green]✓ Whisper model loaded[/green]')

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        console.print(f'[cyan]Transcribing with Whisper: {audio_path.name}[/cyan]')
        if not audio_path.exists():
            raise FileNotFoundError(f'Audio file not found: {audio_path}')
        language_code = WhisperUtils.get_language_code(self.language)
        segments, info = self.model.transcribe(str(audio_path), language=language_code, beam_size=10, word_timestamps=True, condition_on_previous_text=False)
        result = WhisperUtils.build_transcription_result(segments, language=info.language)
        console.print(f'[green]✓ Transcription completed: {audio_path.name}[/green]')
        return result

    def get_name(self) -> str:
        return f'Whisper-{self.model_name}'

    def cleanup(self) -> None:
        console.print('[cyan]Unloading Whisper model and clearing GPU memory...[/cyan]')
        if hasattr(self, 'model'):
            del self.model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        console.print('[green]✓ Whisper model unloaded, GPU memory cleared[/green]')
