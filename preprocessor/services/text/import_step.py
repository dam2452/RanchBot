from __future__ import annotations

import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.step_configs import TranscriptionImportConfig
from preprocessor.core.artifacts import (
    SourceVideo,
    TranscriptionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import JsonFileOutput
from preprocessor.services.episodes.episode_manager import EpisodeManager
from preprocessor.services.episodes.types import EpisodeInfo


class TranscriptionImportStep(PipelineStep[SourceVideo, TranscriptionData, TranscriptionImportConfig]):
    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[SourceVideo], context: ExecutionContext,
    ) -> List[TranscriptionData]:
        return self._execute_with_threadpool(
            input_data, context, 4, self.execute,
        )

    def _process(self, input_data: SourceVideo, context: ExecutionContext) -> TranscriptionData:
        episode_info = input_data.episode_info

        json_file = self.__find_transcription_file(episode_info)
        if not json_file:
            raise FileNotFoundError(
                f'No transcription file found for {input_data.episode_id} in {self.config.source_dir}',
            )

        output_path = self._get_cache_path(input_data, context)
        source_data = self.__load_json(json_file)
        converted_data = self.__convert_data(source_data, json_file)
        converted_data['episode_info'] = EpisodeManager.get_metadata(episode_info)
        self.__save_converted_data(output_path, converted_data)

        context.logger.info(f'Imported {input_data.episode_id} from {json_file.name}')

        trans_meta = converted_data.get('transcription', {})
        return TranscriptionData(
            episode_id=input_data.episode_id,
            episode_info=episode_info,
            path=output_path,
            language=trans_meta.get('language_code', 'pl'),
            model=trans_meta.get('format', '11labs'),
            format='json',
        )

    def get_output_descriptors(self) -> List[JsonFileOutput]:
        return [
            JsonFileOutput(
                pattern='{season}/{episode_num}/{episode}.json',
                subdir='transcriptions/raw',
                min_size_bytes=50,
            ),
        ]

    def _get_cache_path(self, input_data: SourceVideo, context: ExecutionContext) -> Path:
        return self._resolve_output_path(
            0,
            context,
            {
                'season': input_data.episode_info.season_code(),
                'episode_num': input_data.episode_info.episode_num(),
                'episode': input_data.episode_info.episode_code(),
            },
        )

    def _load_from_cache(
        self, cache_path: Path, input_data: SourceVideo, context: ExecutionContext,
    ) -> TranscriptionData:
        return TranscriptionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=cache_path,
            language='pl',
            model='11labs',
            format='json',
        )

    def __find_transcription_file(self, episode_info: EpisodeInfo) -> Optional[Path]:
        file_season = self.__resolve_file_season(episode_info.season)
        ep = episode_info.relative_episode
        pattern = (
            f'*S{file_season:02d}E{ep:02d}*_segmented.json'
            if self.config.format_type == '11labs_segmented'
            else f'*S{file_season:02d}E{ep:02d}*.json'
        )
        files = sorted(self.config.source_dir.rglob(pattern))
        return files[0] if files else None

    def __resolve_file_season(self, target_season: int) -> int:
        for file_season_str, mapped_season in self.config.season_remap.items():
            if mapped_season == target_season:
                return int(file_season_str)
        return target_season

    def __convert_data(self, data: Dict[str, Any], source_file: Path) -> Dict[str, Any]:
        if self.config.format_type == '11labs_segmented':
            return self.__convert_11labs_segmented(data, source_file)
        if self.config.format_type == '11labs':
            return self.__convert_11labs_full(data, source_file)
        raise ValueError(f'Unknown format type: {self.config.format_type}')

    @staticmethod
    def __convert_11labs_full(data: Dict[str, Any], source_file: Path) -> Dict[str, Any]:
        segments: List[Dict[str, Any]] = []
        words = data.get('words', [])
        current_seg: Dict[str, Any] = {
            'words': [], 'start': None, 'end': None, 'text': '', 'speaker': 'unknown',
        }

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
            'transcription': {
                'format': '11labs_segmented',
                'source_file': source_file.name,
                'language_code': 'pol',
            },
            'segments': segments,
        }

    @staticmethod
    def __load_json(file_path: Path) -> Dict[str, Any]:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def __save_converted_data(output_path: Path, data: Dict[str, Any]) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
