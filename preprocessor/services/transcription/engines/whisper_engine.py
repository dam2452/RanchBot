import gc
import json
from pathlib import Path
import subprocess
import tempfile
from typing import (
    Any,
    Dict,
    List,
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
            max_chunk_duration_seconds: int = 1800,
    ) -> None:
        self.__model_name = model_name
        self.__language = language
        self.__device = device
        self.__beam_size = beam_size
        self.__temperature = temperature
        self.__max_chunk_duration_seconds = max_chunk_duration_seconds

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

        duration = self.__get_duration(audio_path)
        if duration > self.__max_chunk_duration_seconds:
            n_chunks = int(duration // self.__max_chunk_duration_seconds) + 1
            console.print(
                f'[yellow]Long audio ({duration/3600:.1f}h), splitting into {n_chunks} chunks '
                f'of {self.__max_chunk_duration_seconds//60}min each[/yellow]',
            )
            result = self.__transcribe_chunked(audio_path, duration)
        else:
            result = self.__transcribe_single(audio_path)

        console.print(f'[green]Transcription completed: {audio_path.name}[/green]')
        return result

    def __transcribe_chunked(self, audio_path: Path, total_duration: float) -> Dict[str, Any]:
        chunk_starts = list(range(0, int(total_duration), self.__max_chunk_duration_seconds))
        all_segments: List[Dict[str, Any]] = []
        text_parts: List[str] = []
        language: Optional[str] = None

        id_offset = 0
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, start in enumerate(chunk_starts):
                end = min(start + self.__max_chunk_duration_seconds, total_duration)
                chunk_path = Path(tmpdir) / f'chunk_{i:04d}.wav'

                console.print(
                    f'[cyan]Chunk {i+1}/{len(chunk_starts)}: '
                    f'{start/3600:.2f}h - {end/3600:.2f}h[/cyan]',
                )
                self.__extract_audio_chunk(audio_path, chunk_path, start, end)

                chunk_result = self.__transcribe_single(chunk_path)

                if language is None:
                    language = chunk_result.get('language')

                offset = float(start)
                chunk_segments = chunk_result.get('segments', [])
                for seg in chunk_segments:
                    adjusted_seg = {
                        **seg,
                        'id': seg['id'] + id_offset,
                        'start': seg['start'] + offset,
                        'end': seg['end'] + offset,
                    }
                    if adjusted_seg.get('words'):
                        adjusted_seg['words'] = [
                            {**w, 'start': w['start'] + offset, 'end': w['end'] + offset}
                            for w in adjusted_seg['words']
                        ]
                    all_segments.append(adjusted_seg)

                id_offset += len(chunk_segments)
                text_parts.append(chunk_result.get('text', ''))

        result: Dict[str, Any] = {'text': ''.join(text_parts), 'segments': all_segments}
        if language:
            result['language'] = language
        return result

    def __transcribe_single(self, audio_path: Path) -> Dict[str, Any]:
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
            vad_filter=True,
        )
        return WhisperUtils.build_transcription_result(segments, language=info.language)

    def __load_model(self) -> WhisperModel:
        compute_type = 'float16'
        console.print(f'[cyan]Loading Whisper: {self.__model_name} on {self.__device} ({compute_type})[/cyan]')

        model = WhisperModel(self.__model_name, device=self.__device, compute_type=compute_type)
        console.print('[green]Whisper model loaded[/green]')
        return model

    @staticmethod
    def __get_duration(path: Path) -> float:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(json.loads(result.stdout)['format']['duration'])

    @staticmethod
    def __extract_audio_chunk(video_path: Path, output_path: Path, start: float, end: float) -> None:
        subprocess.run(
            [
                'ffmpeg', '-y',
                '-ss', str(start), '-to', str(end),
                '-i', str(video_path),
                '-vn', '-acodec', 'pcm_f32le', '-ar', '16000', '-ac', '1',
                str(output_path),
            ],
            capture_output=True, check=True,
        )
