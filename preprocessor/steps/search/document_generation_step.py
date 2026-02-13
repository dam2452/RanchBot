import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Tuple,
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
    @property
    def name(self) -> str:
        return 'document_generation'

    def execute(
            self, input_data: Artifact, context: ExecutionContext,
    ) -> ElasticDocuments:
        episode_info, episode_id = self.__extract_episode_info(input_data)
        output_dir = self.__resolve_output_dir(episode_info, context)

        if self._check_cache_validity(output_dir, context, episode_id, 'cached'):
            return self.__construct_elastic_documents(episode_id, episode_info, output_dir, 0)

        context.logger.info(f'Generating Elasticsearch documents for {episode_id}')
        context.mark_step_started(self.name, episode_id)

        data = self.__gather_input_data(episode_info, context)
        total_docs = self.__generate_documents(data, episode_info, context)

        context.mark_step_completed(self.name, episode_id)
        return self.__construct_elastic_documents(episode_id, episode_info, output_dir, total_docs)

    def __generate_documents(
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

    def __generate_segments_jsonl(
            self, data: Dict[str, Any], episode_info: Any, context: ExecutionContext,
    ) -> Tuple[Path, int]:
        output_path = self.__resolve_segments_output_path(episode_info, context)
        segments = data['transcription'].get('segments', [])
        episode_metadata = self.__build_episode_metadata(episode_info, context)
        video_bot_path = self.__build_video_bot_path(episode_info, context)

        count = self.__write_segments_to_jsonl(
            segments, output_path, episode_info, episode_metadata, video_bot_path,
        )
        return output_path, count

    @staticmethod
    def __write_segments_to_jsonl(
            segments: List[Dict[str, Any]],
            output_path: Path,
            episode_info: Any,
            episode_metadata: Dict[str, Any],
            video_bot_path: str,
    ) -> int:
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
        return count

    @staticmethod
    def __extract_episode_info(input_data: Artifact) -> Tuple[Any, str]:
        if not hasattr(input_data, 'episode_info'):
            raise ValueError('Input artifact must have episode_info')

        episode_info = getattr(input_data, 'episode_info')
        episode_id = getattr(input_data, 'episode_id')
        return episode_info, episode_id

    @staticmethod
    def __resolve_output_dir(episode_info: Any, context: ExecutionContext) -> Path:
        return context.get_output_path(episode_info, 'elastic_documents', '')

    @staticmethod
    def __resolve_segments_output_path(episode_info: Any, context: ExecutionContext) -> Path:
        output_filename = f'{context.series_name}_{episode_info.episode_code()}_text_segments.jsonl'
        return context.get_output_path(
            episode_info, 'elastic_documents/text_segments', output_filename,
        )

    @staticmethod
    def __build_video_bot_path(episode_info: Any, context: ExecutionContext) -> str:
        filename = f'{context.series_name}_{episode_info.episode_code()}.mp4'
        return f'bot/{context.series_name.upper()}-WIDEO/{episode_info.season_code()}/{filename}'

    @staticmethod
    def __construct_elastic_documents(
            episode_id: str, episode_info: Any, output_dir: Path, document_count: int,
    ) -> ElasticDocuments:
        return ElasticDocuments(
            episode_id=episode_id,
            episode_info=episode_info,
            path=output_dir,
            document_count=document_count,
        )

    @staticmethod
    def __build_episode_metadata(episode_info: Any, context: ExecutionContext) -> Dict[str, Any]:
        return {
            'season': episode_info.season,
            'episode_number': episode_info.relative_episode,
            'series_name': context.series_name,
        }

    @staticmethod
    def __gather_input_data(episode_info: Any, context: ExecutionContext) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        clean_path = DocumentGeneratorStep.__resolve_input_path(
            episode_info, context, 'transcriptions/clean', '_clean_transcription.json',
        )
        if clean_path.exists():
            data['transcription'] = FileOperations.load_json(clean_path)

        text_emb_path = DocumentGeneratorStep.__resolve_input_path(
            episode_info, context, 'embeddings', '_embeddings_text.json',
        )
        if text_emb_path.exists():
            data['text_embeddings'] = FileOperations.load_json(text_emb_path)

        scene_path = DocumentGeneratorStep.__resolve_input_path(
            episode_info, context, 'scene_timestamps', '_scenes.json',
        )
        if scene_path.exists():
            data['scenes'] = FileOperations.load_json(scene_path)

        return data

    @staticmethod
    def __resolve_input_path(
            episode_info: Any, context: ExecutionContext, folder: str, suffix: str,
    ) -> Path:
        filename = f'{context.series_name}_{episode_info.episode_code()}{suffix}'
        return context.get_output_path(episode_info, folder, filename)
