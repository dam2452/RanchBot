import json
from pathlib import Path
import time
from typing import (
    Any,
    Dict,
    Optional,
)

from elevenlabs.client import ElevenLabs
from elevenlabs.core import ApiError

from preprocessor.config.config import settings
from preprocessor.services.core.logging import ErrorHandlingLogger
from preprocessor.services.transcription.engines.base_engine import TranscriptionEngine
from preprocessor.services.ui.console import console


class ElevenLabsEngine(TranscriptionEngine):

    def __init__(
        self,
        logger: ErrorHandlingLogger,
        model_id: Optional[str]=None,
        language_code: Optional[str]=None,
        diarize: Optional[bool]=None,
        polling_interval: Optional[int]=None,
    ):
        if not settings.elevenlabs.api_key:
            raise ValueError('ElevenLabs API key not provided. Set ELEVEN_API_KEY environment variable.')
        self.client = ElevenLabs(api_key=settings.elevenlabs.api_key)
        self.model_id = model_id or settings.elevenlabs.model_id
        self.language_code = language_code or settings.elevenlabs.language_code
        self.diarize = diarize if diarize is not None else settings.elevenlabs.diarize
        self.polling_interval = polling_interval or settings.elevenlabs.polling_interval
        self.additional_formats = [
            {'format': 'srt'},
            {
                'format': 'segmented_json',
                'include_speakers': True,
                'include_timestamps': True,
                'segment_on_silence_longer_than_s': 0.5,
                'max_segment_duration_s': 10.0,
                'max_segment_chars': 200,
            },
        ]
        self._logger: ErrorHandlingLogger = logger

    def get_name(self) -> str:
        return 'ElevenLabs'

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        console.print(f'[cyan]Transcribing with 11labs: {audio_path.name}[/cyan]')
        if not audio_path.exists():
            raise FileNotFoundError(f'Audio file not found: {audio_path}')
        transcription_id = self.__submit_job(audio_path)
        result = self.__poll_for_results(transcription_id)
        console.print(f'[green]Transcription completed: {audio_path.name}[/green]')
        return self.__convert_to_unified_format(result)

    @staticmethod
    def __convert_to_unified_format(result) -> Dict[str, Any]:
        unified_data = {'text': result.text, 'language_code': result.language_code, 'segments': []}
        if result.additional_formats:
            for fmt in result.additional_formats:
                if fmt.requested_format == 'segmented_json':
                    segmented_data = json.loads(fmt.content)
                    for seg in segmented_data.get('segments', []):
                        words = seg.get('words', [])
                        if not words:
                            continue
                        non_spacing_words = [w for w in words if w.get('type') != 'spacing']
                        segment = {'text': seg.get('text', '').strip(), 'words': words}
                        if non_spacing_words:
                            first_word = non_spacing_words[0]
                            last_word = non_spacing_words[-1]
                            segment['start'] = first_word.get('start')
                            segment['end'] = last_word.get('end')
                            segment['speaker'] = first_word.get('speaker_id')
                        unified_data['segments'].append(segment)
                    break
        return unified_data

    def __poll_for_results(self, transcription_id: str):
        self._logger.info(f'Polling for results (ID: {transcription_id})...')
        max_attempts = settings.elevenlabs.max_attempts
        attempt = 0
        while attempt < max_attempts:
            try:
                result = self.client.speech_to_text.transcripts.get(transcription_id=transcription_id)
                self._logger.info('Transcription complete!')
                return result
            except ApiError as e:
                if e.status_code == 404:
                    self._logger.info('   ...Processing. Waiting...')
                    time.sleep(self.polling_interval)
                    attempt += 1
                else:
                    self._logger.error(f'API error during polling: {e.body}')
                    raise
        raise TimeoutError(f'Transcription timeout after {max_attempts} attempts')

    def __submit_job(self, audio_path: Path) -> str:
        try:
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            submit_response = self.client.speech_to_text.convert(
                file=audio_data,
                model_id=self.model_id,
                language_code=self.language_code,
                tag_audio_events=True,
                timestamps_granularity='character',
                diarize=self.diarize,
                use_multi_channel=False,
                additional_formats=self.additional_formats,
                webhook=True,
            )
            self._logger.info(f'Job submitted. ID: {submit_response.transcription_id}')
            return submit_response.transcription_id
        except ApiError as e:
            self._logger.error(f'API error during job submission: {e.body}')
            raise
