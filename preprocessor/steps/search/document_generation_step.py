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
from preprocessor.core.output_descriptors import FileOutput
from preprocessor.core.temp_files import StepTempFile
from preprocessor.services.io.files import FileOperations


class DocumentGeneratorStep(PipelineStep[Artifact, ElasticDocuments, DocumentGenerationConfig]):
    @property
    def name(self) -> str:
        return 'document_generation'

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[Artifact], context: ExecutionContext,
    ) -> List[ElasticDocuments]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: Artifact, context: ExecutionContext,
    ) -> ElasticDocuments:
        episode_info, episode_id = self.__extract_episode_info(input_data)
        output_path = self._get_cache_path(input_data, context)

        data = self.__gather_input_data(episode_info, context)
        total_docs = self.__generate_documents(
            data, output_path, episode_info, context,
        )

        return self.__construct_elastic_documents(
            episode_id, episode_info, output_path, total_docs,
        )

    def _get_output_descriptors(self) -> List[FileOutput]:
        return [
            FileOutput(
                pattern="{season}/{episode}.ndjson",
                subdir="elastic_documents",
                min_size_bytes=100,
            ),
        ]

    def _get_cache_path(
        self, input_data: Artifact, context: ExecutionContext,
    ) -> Path:
        episode_info, _ = self.__extract_episode_info(input_data)
        return self._resolve_output_path(
            0,
            context,
            {
                'season': episode_info.season_code(),
                'episode': episode_info.episode_code(),
            },
        )

    def _load_from_cache(
        self, cache_path: Path, input_data: Artifact, context: ExecutionContext,
    ) -> ElasticDocuments:
        episode_info, episode_id = self.__extract_episode_info(input_data)
        return self.__construct_elastic_documents(
            episode_id, episode_info, cache_path, 0,
        )

    def __generate_documents(
        self,
        data: Dict[str, Any],
        output_path: Path,
        episode_info: Any,
        context: ExecutionContext,
    ) -> int:
        total_docs = 0
        if self.config.generate_segments and 'transcription' in data:
            total_docs += self.__generate_segments_jsonl(
                data, output_path, episode_info, context,
            )
        return total_docs

    def __generate_segments_jsonl(
        self,
        data: Dict[str, Any],
        output_path: Path,
        episode_info: Any,
        context: ExecutionContext,
    ) -> int:
        segments = data['transcription'].get('segments', [])
        episode_metadata = self.__build_episode_metadata(episode_info, context)
        video_bot_path = self.__build_video_bot_path(episode_info, context)

        return self.__write_segments_to_jsonl(
            segments,
            output_path,
            episode_info,
            episode_metadata,
            video_bot_path,
        )

    def __gather_input_data(
        self, episode_info: Any, context: ExecutionContext,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        clean_path = self.__resolve_input_path(
            episode_info,
            context,
            'transcriptions/clean',
            '_clean_transcription.json',
        )
        if clean_path.exists():
            data['transcription'] = FileOperations.load_json(clean_path)

        text_emb_path = self.__resolve_input_path(
            episode_info,
            context,
            'embeddings',
            '_embeddings_text.json',
        )
        if text_emb_path.exists():
            data['text_embeddings'] = FileOperations.load_json(text_emb_path)

        scene_path = self.__resolve_input_path(
            episode_info,
            context,
            'scene_timestamps',
            '_scenes.json',
        )
        if scene_path.exists():
            data['scenes'] = FileOperations.load_json(scene_path)

        return data

    @staticmethod
    def __write_segments_to_jsonl(
        segments: List[Dict[str, Any]],
        output_path: Path,
        episode_info: Any,
        episode_metadata: Dict[str, Any],
        video_bot_path: str,
    ) -> int:
        count = 0
        with StepTempFile(output_path) as temp_path:
            with open(temp_path, 'w', encoding='utf-8') as f:
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
    def __build_video_bot_path(episode_info: Any, context: ExecutionContext) -> str:
        filename = f'{context.series_name}_{episode_info.episode_code()}.mp4'
        return (
            f'bot/{context.series_name.upper()}-WIDEO/'
            f'{episode_info.season_code()}/{filename}'
        )

    @staticmethod
    def __construct_elastic_documents(
        episode_id: str,
        episode_info: Any,
        output_path: Path,
        document_count: int,
    ) -> ElasticDocuments:
        return ElasticDocuments(
            episode_id=episode_id,
            episode_info=episode_info,
            path=output_path,
            document_count=document_count,
        )

    @staticmethod
    def __build_episode_metadata(
        episode_info: Any, context: ExecutionContext,
    ) -> Dict[str, Any]:
        return {
            'season': episode_info.season,
            'episode_number': episode_info.relative_episode,
            'series_name': context.series_name,
        }

    @staticmethod
    def __resolve_input_path(
        episode_info: Any,
        context: ExecutionContext,
        folder: str,
        suffix: str,
    ) -> Path:
        filename = f'{context.series_name}_{episode_info.episode_code()}{suffix}'
        return context.get_output_path(episode_info, folder, filename)
