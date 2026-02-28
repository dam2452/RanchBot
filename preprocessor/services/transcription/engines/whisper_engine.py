import gc
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
)

from faster_whisper import WhisperModel
import torch

from preprocessor.services.transcription.engines.base_engine import TranscriptionEngine
from preprocessor.services.transcription.utils import WhisperUtils
from preprocessor.services.ui.console import console


class WhisperEngine(TranscriptionEngine):
    def __init__(
            self,
            model_name: str = 'large-v3-turbo',
            language: str = 'Polish',
            device: str = 'cuda',
            beam_size: int = 10,
            temperature: float = 0.0,
    ) -> None:
        self.__model_name = model_name
        self.__language = language
        self.__device = device
        self.__beam_size = beam_size
        self.__temperature = temperature

        if device != 'cuda':
            raise ValueError(f'Whisper acceleration requires CUDA, got: {device}')

        self.__model: Optional[WhisperModel] = self.__load_model()

    def cleanup(self) -> None:
        console.print('[cyan]Unloading Whisper model and clearing GPU memory...[/cyan]')
        if self.__model:
            del self.__model
            self.__model = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        console.print('[green]Whisper model unloaded, GPU memory cleared[/green]')

    def get_name(self) -> str:
        return f'Whisper-{self.__model_name}'

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        console.print(f'[cyan]Transcribing with Whisper: {audio_path.name}[/cyan]')

        if not audio_path.exists():
            raise FileNotFoundError(f'Audio file not found: {audio_path}')
        if not self.__model:
            raise RuntimeError('Whisper model not loaded.')

        language_code = WhisperUtils.get_language_code(self.__language)

        segments, info = self.__model.transcribe(
            str(audio_path),
            language=language_code,
            beam_size=self.__beam_size,
            word_timestamps=True,
            condition_on_previous_text=False,
            temperature=self.__temperature,
        )

        result = WhisperUtils.build_transcription_result(segments, language=info.language)
        console.print(f'[green]Transcription completed: {audio_path.name}[/green]')
        return result

    def __load_model(self) -> WhisperModel:
        compute_type = 'float16'
        console.print(f'[cyan]Loading Whisper: {self.__model_name} on {self.__device} ({compute_type})[/cyan]')

        model = WhisperModel(self.__model_name, device=self.__device, compute_type=compute_type)
        console.print('[green]Whisper model loaded[/green]')
        return model
