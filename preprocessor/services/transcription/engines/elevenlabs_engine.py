import json
from pathlib import Path
import time
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from elevenlabs.client import ElevenLabs
from elevenlabs.core import ApiError

from preprocessor.config.settings_instance import settings
from preprocessor.services.core.logging import ErrorHandlingLogger
from preprocessor.services.transcription.engines.base_engine import TranscriptionEngine
from preprocessor.services.ui.console import console


class ElevenLabsEngine(TranscriptionEngine):
    def __init__(
            self,
            logger: ErrorHandlingLogger,
            model_id: Optional[str] = None,
            language_code: Optional[str] = None,
            diarize: Optional[bool] = None,
            polling_interval: Optional[int] = None,
    ) -> None:
        self.__validate_api_key()

        self.__client = ElevenLabs(api_key=settings.elevenlabs.api_key)
        self.__logger = logger
        self.__model_id = model_id or settings.elevenlabs.model_id
        self.__language_code = language_code or settings.elevenlabs.language_code
        self.__diarize = diarize if diarize is not None else settings.elevenlabs.diarize
        self.__polling_interval = polling_interval or settings.elevenlabs.polling_interval

        self.__additional_formats: List[Dict[str, Any]] = [
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

    def get_name(self) -> str:
        return 'ElevenLabs'

    def transcribe(self, audio_path: Path) -> Dict[str, Any]:
        console.print(f'[cyan]Transcribing with ElevenLabs: {audio_path.name}[/cyan]')

        if not audio_path.exists():
            raise FileNotFoundError(f'Audio file not found: {audio_path}')

        job_id = self.__submit_job(audio_path)
        raw_result = self.__poll_for_results(job_id)

        console.print(f'[green]Transcription completed: {audio_path.name}[/green]')
        return self.__convert_to_unified_format(raw_result)

    def __submit_job(self, audio_path: Path) -> str:
        try:
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()

            response = self.__client.speech_to_text.convert(
                file=audio_data,
                model_id=self.__model_id,
                language_code=self.__language_code,
                tag_audio_events=True,
                timestamps_granularity='character',
                diarize=self.__diarize,
                use_multi_channel=False,
                additional_formats=self.__additional_formats,
                webhook=True,
            )
            self.__logger.info(f'Job submitted. ID: {response.transcription_id}')
            return response.transcription_id
        except ApiError as e:
            self.__logger.error(f'API error during job submission: {e.body}')
            raise

    def __poll_for_results(self, transcription_id: str) -> Any:
        self.__logger.info(f'Polling for results (ID: {transcription_id})...')
        max_attempts = settings.elevenlabs.max_attempts

        for _attempt in range(max_attempts):
            try:
                result = self.__client.speech_to_text.transcripts.get(transcription_id=transcription_id)
                self.__logger.info('Transcription ready!')
                return result
            except ApiError as e:
                if e.status_code == 404:
                    time.sleep(self.__polling_interval)
                else:
                    self.__logger.error(f'API error during polling: {e.body}')
                    raise

        raise TimeoutError(f'Transcription timeout after {max_attempts} attempts')

    @staticmethod
    def __convert_to_unified_format(result: Any) -> Dict[str, Any]:
        unified_data = {
            'text': result.text,
            'language_code': result.language_code,
            'segments': [],
        }

        if not result.additional_formats:
            return unified_data

        for fmt in result.additional_formats:
            if fmt.requested_format == 'segmented_json':
                segmented_data = json.loads(fmt.content)
                for seg in segmented_data.get('segments', []):
                    segment = ElevenLabsEngine.__parse_segment(seg)
                    if segment:
                        unified_data['segments'].append(segment)
                break
        return unified_data

    @staticmethod
    def __parse_segment(seg_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        words = seg_data.get('words', [])
        if not words:
            return None

        non_spacing = [w for w in words if w.get('type') != 'spacing']
        segment = {
            'text': seg_data.get('text', '').strip(),
            'words': words,
        }

        if non_spacing:
            segment['start'] = non_spacing[0].get('start')
            segment['end'] = non_spacing[-1].get('end')
            segment['speaker'] = non_spacing[0].get('speaker_id')

        return segment

    @staticmethod
    def __validate_api_key() -> None:
        if not settings.elevenlabs.api_key:
            raise ValueError('ElevenLabs API key missing in settings.')
