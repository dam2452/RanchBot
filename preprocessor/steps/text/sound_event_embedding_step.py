# pylint: disable=duplicate-code
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
)

from preprocessor.config.step_configs import SoundEventEmbeddingConfig
from preprocessor.core.artifacts import (
    EmbeddingCollection,
    TranscriptionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import FileOutput
from preprocessor.services.io.files import FileOperations
from preprocessor.services.io.metadata import MetadataBuilder
from preprocessor.services.search.embedding_model import EmbeddingModelWrapper

_SOUND_TYPE_PATTERN = re.compile(r'\(([^)]+)\)')


class SoundEventEmbeddingStep(
    PipelineStep[TranscriptionData, EmbeddingCollection, SoundEventEmbeddingConfig],
):
    def __init__(self, config: SoundEventEmbeddingConfig) -> None:
        super().__init__(config)
        self.__model: Optional[EmbeddingModelWrapper] = None

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__model is None:
            context.logger.info(f'Loading embedding model: {self.config.model_name}')
            self.__model = EmbeddingModelWrapper(
                self.config.model_name,
                self.config.device,
                self.config.batch_size,
            )

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__model:
            self.__model = None
            context.logger.info('Embedding model unloaded')

    def cleanup(self) -> None:
        if self.__model:
            self.__model = None

    def execute_batch(
        self,
        input_data: List[TranscriptionData],
        context: ExecutionContext,
    ) -> List[EmbeddingCollection]:
        return self._execute_sequential(input_data, context, self.execute)

    def _process(
        self,
        input_data: TranscriptionData,
        context: ExecutionContext,
    ) -> EmbeddingCollection:
        output_path = self._get_cache_path(input_data, context)

        segments = self.__load_segments(input_data, context)
        if not segments:
            return self.__build_collection(input_data, output_path, 0)

        self.__ensure_model()
        context.logger.info(f'Generating sound event embeddings for {input_data.episode_id}')

        results = self.__process_chunks(segments)
        self.__save_results(results, output_path, input_data)

        return self.__build_collection(input_data, output_path, len(results))

    def get_output_descriptors(self) -> List[FileOutput]:
        return [
            FileOutput(
                pattern="{season}/{episode}.json",
                subdir="embeddings/sound_events",
                min_size_bytes=1024,
            ),
        ]

    def _get_cache_path(
        self,
        input_data: TranscriptionData,
        context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            self.__create_path_vars(input_data),
        )

    def _load_from_cache(
        self,
        cache_path: Path,
        input_data: TranscriptionData,
        context: ExecutionContext,
    ) -> EmbeddingCollection:
        data: Dict[str, Any] = FileOperations.load_json(cache_path)
        return self.__build_collection(
            input_data,
            cache_path,
            len(data.get('sound_event_embeddings', [])),
        )

    def __ensure_model(self) -> None:
        if self.__model is None:
            self.__model = EmbeddingModelWrapper(
                self.config.model_name,
                self.config.device,
                self.config.batch_size,
            )

    def __process_chunks(
        self,
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        chunks = self.__group_segments(segments)
        if not self.__model:
            raise RuntimeError("Embedding model not initialized")

        results: List[Dict[str, Any]] = []
        for i in range(0, len(chunks), self.config.batch_size):
            batch_chunks = chunks[i : i + self.config.batch_size]
            batch_texts = [c['text'] for c in batch_chunks]
            batch_embeddings: List[List[float]] = self.__model.encode_text(batch_texts)
            for chunk, embedding in zip(batch_chunks, batch_embeddings):
                results.append({**chunk, 'embedding': embedding})

        return results

    def __group_segments(
        self,
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        chunks: List[Dict[str, Any]] = []
        step = self.config.segments_per_embedding

        for i in range(0, len(segments), step):
            chunk_segs = segments[i : i + step]
            if not chunk_segs:
                continue

            text = ' '.join(s.get('text', '') for s in chunk_segs).strip()
            if not text:
                continue

            sound_types: Set[str] = set()
            for seg in chunk_segs:
                for match in _SOUND_TYPE_PATTERN.finditer(seg.get('text', '')):
                    sound_types.add(match.group(1).strip().lower())

            chunks.append({
                'segment_range': [i, i + len(chunk_segs) - 1],
                'text': text,
                'sound_types': sorted(sound_types),
                'start_time': chunk_segs[0].get('start', 0.0),
                'end_time': chunk_segs[-1].get('end', 0.0),
            })

        return chunks

    def __save_results(
        self,
        results: List[Dict[str, Any]],
        output_path: Path,
        input_data: TranscriptionData,
    ) -> None:
        output_data: Dict[str, Any] = MetadataBuilder.create_processing_metadata(
            episode_info=input_data.episode_info,
            processing_params=self.config.model_dump(),
            statistics={
                'total_embeddings': len(results),
                'embedding_dimension': len(results[0]['embedding']) if results else 0,
            },
            results_key='sound_event_embeddings',
            results_data=results,
        )
        FileOperations.atomic_write_json(output_path, output_data)

    def __build_collection(
        self,
        input_data: TranscriptionData,
        output_path: Path,
        embedding_count: int,
    ) -> EmbeddingCollection:
        return MetadataBuilder.create_embedding_collection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            model_name=self.config.model_name,
            embedding_count=embedding_count,
            embedding_type='sound_events',
        )

    @staticmethod
    def __create_path_vars(input_data: TranscriptionData) -> Dict[str, str]:
        return {
            "season": f"S{input_data.episode_info.season:02d}",
            "episode": input_data.episode_info.episode_code(),
        }

    @staticmethod
    def __load_segments(
        input_data: TranscriptionData,
        context: ExecutionContext,
    ) -> List[Dict[str, Any]]:
        data: Dict[str, Any] = FileOperations.load_json(input_data.path)
        segments: List[Dict[str, Any]] = data.get('segments', [])
        if not segments:
            context.logger.warning(
                f'No sound event segments for embedding in {input_data.episode_id}',
            )
        return segments
