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
    def __init__(
            self,
            model: str = 'large-v3-turbo',
            language: str = 'pl',
            device: str = 'cuda',
            beam_size: int = 10,
            temperature: float = 0.0,
    ) -> None:
        self.__model_name = model
        self.__language = language
        self.__device = device
        self.__beam_size = beam_size
        self.__temperature = temperature
        self.__model: Optional[WhisperModel] = None

    def cleanup(self) -> None:
        console.print('[cyan]Unloading Whisper model and clearing GPU memory...[/cyan]')
        if self.__model is not None:
            del self.__model
            self.__model = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        console.print('[green]Whisper model unloaded, GPU memory cleared[/green]')

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        console.print(f'[cyan]Transcribing with Whisper: {audio_path.name}[/cyan]')

        if not audio_path.exists():
            raise FileNotFoundError(f'Audio file not found: {audio_path}')

        model = self.__get_or_load_model()
        language_code = WhisperUtils.get_language_code(self.__language)

        segments, info = model.transcribe(
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

    def __get_or_load_model(self) -> WhisperModel:
        if self.__model is not None:
            return self.__model

        if self.__device != 'cuda':
            raise ValueError(f'Only GPU (cuda) is supported, got device={self.__device}')

        compute_type = 'float16'
        console.print(
            f'[cyan]Loading Whisper: {self.__model_name} on {self.__device} ({compute_type})[/cyan]',
        )

        self.__model = WhisperModel(
            self.__model_name,
            device=self.__device,
            compute_type=compute_type,
        )
        console.print('[green]Whisper model loaded[/green]')
        return self.__model
