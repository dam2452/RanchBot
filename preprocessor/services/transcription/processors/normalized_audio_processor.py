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

from preprocessor.services.core.logging import ErrorHandlingLogger
from preprocessor.services.transcription.whisper import WhisperUtils


class NormalizedAudioProcessor:
    SUPPORTED_AUDIO_EXTENSIONS: Tuple[str, str] = ('.wav', '.mp3')

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
        self.__input_audios = input_audios
        self.__output_dir = output_dir
        self.__logger = logger
        self.__audio_files = audio_files
        self.__language = language

        self.__output_dir.mkdir(parents=True, exist_ok=True)

        if device != 'cuda':
            raise ValueError(f'Whisper acceleration requires CUDA device, got: {device}')

        self.__whisper_model = WhisperModel(
            model,
            device=device,
            compute_type='float16',
        )
        self.__logger.info(f'Whisper {model} initialized on {device}')

    def cleanup(self) -> None:
        self.__logger.info('Purging GPU memory and unloading Whisper model...')
        del self.__whisper_model

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def __call__(self) -> None:
        targets = self.__audio_files if self.__audio_files is not None else self.__discover_audios()
        for audio in targets:
            self.__transcribe_file(audio)

    def __discover_audios(self) -> List[Path]:
        return [
            a for a in self.__input_audios.rglob('*')
            if a.suffix.lower() in self.SUPPORTED_AUDIO_EXTENSIONS
        ]

    def __transcribe_file(self, audio_path: Path) -> None:
        try:
            output_file = self.__output_dir / audio_path.with_suffix('.json').name
            if output_file.exists():
                return

            segments, info = self.__whisper_model.transcribe(
                str(audio_path),
                language=WhisperUtils.get_language_code(self.__language),
                beam_size=10,
                word_timestamps=True,
                condition_on_previous_text=False,
                temperature=0.0,
            )

            result = WhisperUtils.build_transcription_result(segments, language=info.language)
            self.__save_results(result, output_file)
            self.__logger.info(f'Transcription saved: {output_file.name}')

        except Exception as e:
            self.__logger.error(f'Whisper error on {audio_path.name}: {e}')

    @staticmethod
    def __save_results(result: dict, path: Path) -> None:
        for segment in result.get('segments', []):
            segment['temperature'] = 0.0

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
