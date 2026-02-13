from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
)

from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.validators.base_validator import BaseValidator

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class TranscriptionValidator(BaseValidator):
    def validate(self, stats: 'EpisodeStats') -> None:
        trans_files = self.__resolve_file_map(stats)

        if not any(f.exists() for f in trans_files.values()):
            self._add_error(stats, 'No transcription files found in any format')
            return

        self.__validate_raw_transcription(stats, trans_files)
        self.__validate_clean_transcription(stats, trans_files['clean'])
        self.__validate_clean_txt(stats, trans_files['clean_txt'])
        self.__validate_sound_events(stats, trans_files['sound_events'])

    def __validate_raw_transcription(
            self, stats: 'EpisodeStats', trans_files: Dict[str, Path],
    ) -> None:
        # Try to find any available raw format
        raw_path = next((trans_files[k] for k in ('main', 'segmented', 'simple') if trans_files[k].exists()), None)

        if not raw_path:
            self._add_warning(stats, 'Missing raw transcription file (.json, _segmented.json, or _simple.json)')
            return

        if self._validate_json_if_exists(stats, raw_path, "Invalid transcription JSON"):
            self.__extract_transcription_metrics(stats, raw_path)

    def __extract_transcription_metrics(self, stats: 'EpisodeStats', raw_path: Path) -> None:
        data = self._load_json_safely(raw_path)
        if not data:
            self._add_error(stats, f'Error reading transcription: {raw_path}')
            return

        text = self.__get_full_text(data)
        stats.transcription_chars = len(text)
        stats.transcription_words = len(text.split())
        stats.transcription_duration = self.__determine_duration(data)

    def __get_full_text(self, data: Dict[str, Any]) -> str:
        text = data.get('text', '')
        if not text:
            segments: List[Dict[str, Any]] = data.get('segments', [])
            text = ' '.join(s.get('text', '') for s in segments)
        return text

    def __determine_duration(self, data: Dict[str, Any]) -> float:
        words: List[Dict[str, Any]] = data.get('words', [])
        if words:
            return words[-1].get('end', 0.0)

        segments: List[Dict[str, Any]] = data.get('segments', [])
        if segments and segments[-1].get('end'):
            return segments[-1].get('end', 0.0)
        return 0.0

    def __validate_clean_transcription(self, stats: 'EpisodeStats', file_path: Path) -> None:
        self._validate_json_with_warning(
            stats, file_path,
            missing_msg=f'Missing clean transcription: {file_path.name}',
            invalid_msg_prefix='Invalid clean transcription JSON',
        )

    def __validate_clean_txt(self, stats: 'EpisodeStats', file_path: Path) -> None:
        if not file_path.exists():
            self._add_warning(stats, f'Missing clean transcription txt: {file_path.name}')

    def __validate_sound_events(self, stats: 'EpisodeStats', file_path: Path) -> None:
        self._validate_json_with_warning(
            stats, file_path,
            missing_msg=f'Missing sound events: {file_path.name}',
            invalid_msg_prefix='Invalid sound events JSON',
        )

    def __resolve_file_map(self, stats: 'EpisodeStats') -> Dict[str, Path]:
        path_svc = PathService(stats.series_name)
        trans_dir = path_svc.get_episode_dir(stats.episode_info, settings.output_subdirs.transcriptions)
        base = f'{stats.series_name}_{stats.episode_info.episode_code()}'

        raw_base = trans_dir / settings.output_subdirs.transcription_subdirs.raw
        clean_base = trans_dir / settings.output_subdirs.transcription_subdirs.clean
        sound_base = trans_dir / settings.output_subdirs.transcription_subdirs.sound_events

        return {
            'main': raw_base / f'{base}.json',
            'segmented': raw_base / f'{base}_segmented.json',
            'simple': raw_base / f'{base}_simple.json',
            'clean': clean_base / f'{base}_clean_transcription.json',
            'clean_txt': clean_base / f'{base}_clean_transcription.txt',
            'sound_events': sound_base / f'{base}_sound_events.json',
        }
