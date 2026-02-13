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
from preprocessor.services.episodes.episode_manager import EpisodeManager

if TYPE_CHECKING:
    from preprocessor.services.episodes.episode_manager import EpisodeInfo


class TranscriptionImportStep(PipelineStep[None, List[TranscriptionData], TranscriptionImportConfig]):
    def __init__(self, config: TranscriptionImportConfig) -> None:
        super().__init__(config)
        self.__episode_manager: Optional[EpisodeManager] = None

    @property
    def name(self) -> str:
        return 'transcription_import'

    def execute(self, input_data: None, context: ExecutionContext) -> List[TranscriptionData]:
        self.__ensure_episode_manager(context)

        json_files = self.__find_transcription_files()
        if not json_files:
            context.logger.warning(f'No transcription files found in {self.config.source_dir}')
            return []

        context.logger.info(f'Found {len(json_files)} transcription files to import')

        results: List[TranscriptionData] = []
        for json_file in json_files:
            try:
                artifact = self.__import_single_file(json_file, context)
                if artifact:
                    results.append(artifact)
            except Exception as e:
                context.logger.error(f'Failed to import {json_file.name}: {e}')

        return results

    def __ensure_episode_manager(self, context: ExecutionContext) -> None:
        if self.__episode_manager is None:
            self.__episode_manager = EpisodeManager(None, context.series_name, context.logger)

    def __find_transcription_files(self) -> List[Path]:
        pattern = '*_segmented.json' if self.config.format_type == '11labs_segmented' else '*.json'
        files = sorted(self.config.source_dir.rglob(pattern))
        return [f for f in files if not f.name.startswith('.')]

    def __import_single_file(self, json_file: Path, context: ExecutionContext) -> Optional[TranscriptionData]:
        episode_info = self.__resolve_episode_info(json_file)
        if not episode_info:
            context.logger.warning(f'Could not determine episode for {json_file}')
            return None

        episode_id = self.__episode_manager.get_episode_id_for_state(episode_info)
        output_path = self.__get_output_path(episode_info, context)

        if self.__should_skip_import(output_path, episode_id, context):
            return self.__construct_cached_artifact(episode_id, episode_info, output_path)

        context.logger.info(f'Importing {episode_id} from {json_file.name}')
        context.mark_step_started(self.name, episode_id)

        source_data = self.__load_json(json_file)
        converted_data = self.__convert_data(source_data, json_file)
        converted_data['episode_info'] = EpisodeManager.get_metadata(episode_info)

        self.__save_converted_data(output_path, converted_data)
        context.mark_step_completed(self.name, episode_id)

        return self.__construct_new_artifact(episode_id, episode_info, output_path, converted_data)

    def __resolve_episode_info(self, json_file: Path) -> Optional['EpisodeInfo']:
        info = self.__episode_manager.parse_filename(json_file)
        if not info:
            season, episode = self.__extract_season_episode_fallback(json_file)
            info = self.__episode_manager.get_episode_by_season_and_relative(season, episode)
        return info

    def __convert_data(self, data: Dict[str, Any], source_file: Path) -> Dict[str, Any]:
        if self.config.format_type == '11labs_segmented':
            return self.__convert_11labs_segmented(data, source_file)
        if self.config.format_type == '11labs':
            return self.__convert_11labs_full(data, source_file)
        raise ValueError(f'Unknown format type: {self.config.format_type}')

    def __should_skip_import(self, output_path: Path, episode_id: str, context: ExecutionContext) -> bool:
        if output_path.exists() and not context.force_rerun:
            context.logger.info(f'Skipping {episode_id} (output exists)')
            if not context.is_step_completed(self.name, episode_id):
                context.mark_step_completed(self.name, episode_id)
            return True
        return False

    def __get_output_path(self, episode_info: 'EpisodeInfo', context: ExecutionContext) -> Path:
        filename = self.__episode_manager.path_manager.build_filename(episode_info, extension='json')
        return context.get_output_path(episode_info, 'transcriptions', filename)

    @staticmethod
    def __convert_11labs_full(data: Dict[str, Any], source_file: Path) -> Dict[str, Any]:
        segments: List[Dict[str, Any]] = []
        words = data.get('words', [])
        current_seg: Dict[str, Any] = {'words': [], 'start': None, 'end': None, 'text': '', 'speaker': 'unknown'}

        for word in words:
            if current_seg['start'] is None:
                current_seg['start'] = word.get('start')

            current_seg['words'].append(word)
            current_seg['end'] = word.get('end')

            if word.get('text', '').endswith(('.', '!', '?')) or len(current_seg['words']) >= 20:
                current_seg['text'] = ' '.join(w.get('text', '') for w in current_seg['words'])
                segments.append(dict(current_seg))
                current_seg = {
                    'words': [], 'start': None, 'end': None, 'text': '',
                    'speaker': word.get('speaker_id', 'unknown'),
                }

        if current_seg['words']:
            current_seg['text'] = ' '.join(w.get('text', '') for w in current_seg['words'])
            segments.append(current_seg)

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
    def __convert_11labs_segmented(data: Dict[str, Any], source_file: Path) -> Dict[str, Any]:
        segments = []
        for i, segment in enumerate(data.get('segments', [])):
            segments.append({
                'id': i,
                'start': segment.get('start'),
                'end': segment.get('end'),
                'text': segment.get('text', ''),
                'speaker': segment.get('speaker', 'unknown'),
                'words': segment.get('words', []),
            })
        return {
            'transcription': {'format': '11labs_segmented', 'source_file': source_file.name, 'segments': segments},
            'segments': segments,
        }

    @staticmethod
    def __extract_season_episode_fallback(file_path: Path) -> Tuple[int, int]:
        match = re.search('S(\\d+)E(\\d+)', file_path.name, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))

        parent_match = re.search('S(\\d+)', file_path.parent.name, re.IGNORECASE)
        if parent_match:
            season = int(parent_match.group(1))
            episode_match = re.search('E(\\d+)', file_path.name, re.IGNORECASE)
            if episode_match:
                return season, int(episode_match.group(1))
        return 1, 1

    @staticmethod
    def __load_json(file_path: Path) -> Dict[str, Any]:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def __save_converted_data(output_path: Path, data: Dict[str, Any]) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def __construct_cached_artifact(episode_id: str, info: 'EpisodeInfo', path: Path) -> TranscriptionData:
        return TranscriptionData(
            episode_id=episode_id, episode_info=info, path=path,
            language='pl', model='11labs', format='json',
        )

    @staticmethod
    def __construct_new_artifact(
        episode_id: str, info: 'EpisodeInfo', path: Path,
        data: Dict[str, Any],
    ) -> TranscriptionData:
        trans_meta = data.get('transcription', {})
        return TranscriptionData(
            episode_id=episode_id,
            episode_info=info,
            path=path,
            language=trans_meta.get('language_code', 'pl'),
            model=trans_meta.get('format', '11labs'),
            format='json',
        )
