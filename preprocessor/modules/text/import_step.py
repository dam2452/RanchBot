import json
from pathlib import Path
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from preprocessor.config.step_configs import TranscriptionImportConfig
from preprocessor.core.artifacts import TranscriptionData
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.lib.episodes.episode_manager import EpisodeManager

if TYPE_CHECKING:
    from preprocessor.lib.episodes.episode_manager import EpisodeInfo

class TranscriptionImportStep(PipelineStep[None, List[TranscriptionData], TranscriptionImportConfig]):

    def __init__(self, config: TranscriptionImportConfig) -> None:
        super().__init__(config)
        self._episode_manager: Optional[EpisodeManager] = None

    @property
    def name(self) -> str:
        return 'transcription_import'

    def execute(self, input_data: None, context: ExecutionContext) -> List[TranscriptionData]:
        if self._episode_manager is None:
            self._episode_manager = EpisodeManager(None, context.series_name, context.logger)
        json_files: List[Path] = self._find_transcription_files()
        if not json_files:
            context.logger.warning(f'No transcription files found in {self.config.source_dir}')
            return []
        context.logger.info(f'Found {len(json_files)} transcription files to import')
        results: List[TranscriptionData] = []
        for json_file in json_files:
            try:
                artifact: Optional[TranscriptionData] = self._import_single_file(json_file, context)
                if artifact:
                    results.append(artifact)
            except Exception as e:
                context.logger.error(f'Failed to import {json_file.name}: {e}')
        return results

    def _find_transcription_files(self) -> List[Path]:
        pattern: str = '*.json'
        if self.config.format_type == '11labs_segmented':
            pattern = '*_segmented.json'
        files: List[Path] = sorted(self.config.source_dir.rglob(pattern))
        return [f for f in files if not f.name.startswith('.')]

    def _import_single_file(self, json_file: Path, context: ExecutionContext) -> Optional[TranscriptionData]:
        episode_info: Optional['EpisodeInfo'] = self._episode_manager.parse_filename(json_file)
        if not episode_info:
            season_num, episode_num = self._extract_season_episode_fallback(json_file)
            episode_info = self._episode_manager.get_episode_by_season_and_relative(season_num, episode_num)
        if not episode_info:
            context.logger.warning(f'Could not determine episode for {json_file}')
            return None
        episode_id: str = self._episode_manager.get_episode_id_for_state(episode_info)
        output_filename: str = self._episode_manager.path_manager.build_filename(episode_info, extension='json')
        output_path: Path = context.get_output_path(episode_info, 'transcriptions', output_filename)
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, episode_id):
                context.logger.info(f'Skipping {episode_id} (cached)')
                return TranscriptionData(episode_id=episode_id, episode_info=episode_info, path=output_path, language='pl', model='11labs', format='json')
        context.logger.info(f'Importing {episode_id} from {json_file.name}')
        context.mark_step_started(self.name, episode_id)
        with open(json_file, 'r', encoding='utf-8') as f:
            source_data: Dict[str, Any] = json.load(f)
        if self.config.format_type == '11labs_segmented':
            converted_data: Dict[str, Any] = self._convert_11labs_segmented(source_data, json_file)
        elif self.config.format_type == '11labs':
            converted_data = self._convert_11labs_full(source_data, json_file)
        else:
            raise ValueError(f'Unknown format type: {self.config.format_type}')
        converted_data['episode_info'] = EpisodeManager.get_metadata(episode_info)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=2, ensure_ascii=False)
        context.mark_step_completed(self.name, episode_id)
        return TranscriptionData(
            episode_id=episode_id,
            episode_info=episode_info,
            path=output_path,
            language=converted_data.get('transcription', {}).get('language_code', 'pl'),
            model=converted_data.get('transcription', {}).get('format', '11labs'),
            format='json',
        )

    @staticmethod
    def _convert_11labs_segmented(data: Dict[str, Any], source_file: Path) -> Dict[str, Any]:
        segments: List[Dict[str, Any]] = []
        for i, segment in enumerate(data.get('segments', [])):
            converted_segment: Dict[str, Any] = {
                'id': i,
                'start': segment.get('start'),
                'end': segment.get('end'),
                'text': segment.get('text', ''),
                'speaker': segment.get('speaker', 'unknown'),
                'words': segment.get('words', []),
            }
            segments.append(converted_segment)
        return {
            'transcription': {'format': '11labs_segmented', 'source_file': source_file.name, 'segments': segments},
            'segments': segments,
        }

    @staticmethod
    def _convert_11labs_full(data: Dict[str, Any], source_file: Path) -> Dict[str, Any]:
        segments: List[Dict[str, Any]] = []
        words: List[Dict[str, Any]] = data.get('words', [])
        current_segment: Dict[str, Any] = {'words': [], 'start': None, 'end': None, 'text': '', 'speaker': 'unknown'}
        for word in words:
            if current_segment['start'] is None:
                current_segment['start'] = word.get('start')
            current_segment['words'].append(word)
            current_segment['end'] = word.get('end')
            if word.get('text', '').endswith(('.', '!', '?')) or len(current_segment['words']) >= 20:
                current_segment['text'] = ' '.join((w.get('text', '') for w in current_segment['words']))
                segments.append(dict(current_segment))
                current_segment = {'words': [], 'start': None, 'end': None, 'text': '', 'speaker': word.get('speaker_id', 'unknown')}
        if current_segment['words']:
            current_segment['text'] = ' '.join((w.get('text', '') for w in current_segment['words']))
            segments.append(current_segment)
        for i, seg in enumerate(segments):
            seg['id'] = i
        return {
            'transcription': {
                'format': '11labs',
                'source_file': source_file.name,
                'language_code': data.get('language_code', 'pol'),
                'language_probability': data.get('language_probability', 1.0),
            },
            'segments': segments,
        }

    @staticmethod
    def _extract_season_episode_fallback(file_path: Path) -> Tuple[int, int]:
        match: Optional[re.Match] = re.search('S(\\d+)E(\\d+)', file_path.name, re.IGNORECASE)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        parent_match: Optional[re.Match] = re.search('S(\\d+)', file_path.parent.name, re.IGNORECASE)
        if parent_match:
            season: int = int(parent_match.group(1))
            episode_match: Optional[re.Match] = re.search('E(\\d+)', file_path.name, re.IGNORECASE)
            if episode_match:
                return (season, int(episode_match.group(1)))
        return (1, 1)
