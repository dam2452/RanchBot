import json
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.config.step_configs import DocumentGenerationConfig
from preprocessor.core.artifacts import (
    Artifact,
    ElasticDocuments,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.io.files import FileOperations


class DocumentGeneratorStep(PipelineStep[Artifact, ElasticDocuments, DocumentGenerationConfig]):

    def execute(self, input_data: Artifact, context: ExecutionContext) -> ElasticDocuments:
        episode_info, episode_id = self._extract_episode_info(input_data)
        output_dir = context.get_output_path(episode_info, 'elastic_documents', '')

        if self._check_cache_validity(output_dir, context, episode_id, 'cached'):
            return self._create_empty_result(episode_id, episode_info, output_dir)

        context.logger.info(f'Generating Elasticsearch documents for {episode_id}')
        context.mark_step_started(self.name, episode_id)

        data = self.__gather_input_data(episode_info, context)
        total_docs = self._generate_documents(data, episode_info, context)

        context.mark_step_completed(self.name, episode_id)
        return ElasticDocuments(
            episode_id=episode_id,
            episode_info=episode_info,
            path=output_dir,
            document_count=total_docs,
        )

    @property
    def name(self) -> str:
        return 'document_generation'

    @staticmethod
    def _extract_episode_info(input_data: Artifact) -> tuple[Any, str]:
        if not hasattr(input_data, 'episode_info'):
            raise ValueError('Input artifact must have episode_info')
        episode_info = getattr(input_data, 'episode_info')
        episode_id = getattr(input_data, 'episode_id')
        return episode_info, episode_id


    @staticmethod
    def _create_empty_result(episode_id: str, episode_info: Any, output_dir: Path) -> ElasticDocuments:
        return ElasticDocuments(
            episode_id=episode_id,
            episode_info=episode_info,
            path=output_dir,
            document_count=0,
        )

    def _generate_documents(
        self,
        data: Dict[str, Any],
        episode_info: Any,
        context: ExecutionContext,
    ) -> int:
        total_docs = 0
        if self.config.generate_segments and 'transcription' in data:
            _, count = self.__generate_segments_jsonl(data, episode_info, context)
            total_docs += count
        return total_docs

    @staticmethod
    def __build_episode_metadata(episode_info: Any, context: ExecutionContext) -> Dict[str, Any]:
        return {'season': episode_info.season, 'episode_number': episode_info.relative_episode, 'series_name': context.series_name}

    @staticmethod
    def __gather_input_data(episode_info: Any, context: ExecutionContext) -> Dict[str, Any]:
        data = {}
        clean_filename = f'{context.series_name}_{episode_info.episode_code()}_clean_transcription.json'
        clean_path = context.get_output_path(episode_info, 'transcriptions/clean', clean_filename)
        if clean_path.exists():
            data['transcription'] = FileOperations.load_json(clean_path)
        text_emb_filename = f'{context.series_name}_{episode_info.episode_code()}_embeddings_text.json'
        text_emb_path = context.get_output_path(episode_info, 'embeddings', text_emb_filename)
        if text_emb_path.exists():
            data['text_embeddings'] = FileOperations.load_json(text_emb_path)
        scene_filename = f'{context.series_name}_{episode_info.episode_code()}_scenes.json'
        scene_path = context.get_output_path(episode_info, 'scene_timestamps', scene_filename)
        if scene_path.exists():
            data['scenes'] = FileOperations.load_json(scene_path)
        return data

    def __generate_segments_jsonl(self, data: Dict[str, Any], episode_info: Any, context: ExecutionContext) -> tuple[Path, int]:
        output_filename = f'{context.series_name}_{episode_info.episode_code()}_text_segments.jsonl'
        output_path = context.get_output_path(episode_info, 'elastic_documents/text_segments', output_filename)
        segments = data['transcription'].get('segments', [])
        episode_metadata = self.__build_episode_metadata(episode_info, context)
        filename = f'{context.series_name}_{episode_info.episode_code()}.mp4'
        video_bot_path = f'bot/{context.series_name.upper()}-WIDEO/{episode_info.season_code()}/{filename}'
        count = 0
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments):
                doc = {
                    'episode_id': episode_info.episode_code(),
                    'episode_metadata': episode_metadata,
                    'segment_id': i,
                    'text': segment.get('text', '').strip(),
                    'start_time': segment.get('start', 0.0),
                    'end_time': segment.get('end', 0.0),
                    'speaker': segment.get('speaker', 'unknown'),
                    'video_path': video_bot_path,
                }
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')
                count += 1
        return output_path, count
