from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Dict,
)

from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class TranscriptionValidator(BaseValidator):

    def validate(self, stats: 'EpisodeStats') -> None:
        transcriptions_dir = PathService(stats.series_name).get_episode_dir(
            stats.episode_info, settings.output_subdirs.transcriptions,
        )
        base_name = f'{stats.series_name}_{stats.episode_info.episode_code()}'
        raw_dir = transcriptions_dir / settings.output_subdirs.transcription_subdirs.raw
        clean_dir = transcriptions_dir / settings.output_subdirs.transcription_subdirs.clean
        sound_events_dir = transcriptions_dir / settings.output_subdirs.transcription_subdirs.sound_events

        transcription_files = {
            'main': raw_dir / f'{base_name}.json',
            'segmented': raw_dir / f'{base_name}_segmented.json',
            'simple': raw_dir / f'{base_name}_simple.json',
            'clean': clean_dir / f'{base_name}_clean_transcription.json',
            'clean_txt': clean_dir / f'{base_name}_clean_transcription.txt',
            'sound_events': sound_events_dir / f'{base_name}_sound_events.json',
        }

        if not any((f.exists() for f in transcription_files.values())):
            self._add_error(stats, 'No transcription files found in any format')
            return

        self.__validate_raw_transcription(stats, transcription_files)
        self.__validate_clean_transcription(stats, transcription_files['clean'])
        self.__validate_clean_txt(stats, transcription_files['clean_txt'])
        self.__validate_sound_events(stats, transcription_files['sound_events'])

    def __validate_raw_transcription(
        self, stats: 'EpisodeStats', transcription_files: Dict[str, Path],
    ) -> None:
        raw_transcription = None
        for key in ('main', 'segmented', 'simple'):
            if transcription_files[key].exists():
                raw_transcription = transcription_files[key]
                break

        if not raw_transcription:
            self._add_warning(
                stats,
                'Missing raw transcription file (checked: .json, _segmented.json, _simple.json)',
            )
            return

        result = FileValidator.validate_json_file(raw_transcription)
        if not result.is_valid:
            self._add_error(stats, f'Invalid transcription JSON: {result.error_message}')
            return

        self.__extract_transcription_stats(stats, raw_transcription)

    def __extract_transcription_stats(self, stats: 'EpisodeStats', raw_transcription: Path) -> None:
        data = self._load_json_safely(raw_transcription)
        if not data:
            self._add_error(stats, f'Error reading transcription: {raw_transcription}')
            return

        text = data.get('text', '')
        if not text:
            segments = data.get('segments', [])
            if segments:
                text = ' '.join((seg.get('text', '') for seg in segments))

        stats.transcription_chars = len(text)
        stats.transcription_words = len(text.split())

        words = data.get('words', [])
        if words:
            stats.transcription_duration = words[-1].get('end', 0.0)
        else:
            segments = data.get('segments', [])
            if segments and segments[-1].get('end'):
                stats.transcription_duration = segments[-1].get('end', 0.0)


    def __validate_clean_transcription(self, stats: 'EpisodeStats', clean_transcription_file: Path) -> None:
        self._validate_json_with_warning(
            stats,
            clean_transcription_file,
            missing_msg=f'Missing clean transcription file: {clean_transcription_file.name}',
            invalid_msg_prefix='Invalid clean transcription JSON',
        )

    def __validate_clean_txt(self, stats: 'EpisodeStats', clean_txt_file: Path) -> None:
        if not clean_txt_file.exists():
            self._add_warning(stats, f'Missing clean transcription txt: {clean_txt_file.name}')

    def __validate_sound_events(self, stats: 'EpisodeStats', sound_events_file: Path) -> None:
        self._validate_json_with_warning(
            stats,
            sound_events_file,
            missing_msg=f'Missing sound events file: {sound_events_file.name}',
            invalid_msg_prefix='Invalid sound events JSON',
        )
