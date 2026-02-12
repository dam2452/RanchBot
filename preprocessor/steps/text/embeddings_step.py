from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.step_configs import TextEmbeddingConfig
from preprocessor.core.artifacts import (
    EmbeddingCollection,
    TranscriptionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.io.files import (
    atomic_write_json,
    load_json,
)
from preprocessor.services.io.metadata import MetadataBuilder
from preprocessor.services.search.embedding_model import EmbeddingModelWrapper


class TextEmbeddingStep(PipelineStep[TranscriptionData, EmbeddingCollection, TextEmbeddingConfig]):

    def __init__(self, config: TextEmbeddingConfig) -> None:
        super().__init__(config)
        self._model: Optional[EmbeddingModelWrapper] = None

    def cleanup(self) -> None:
        if self._model:
            self._model = None

    def execute(
        self,
        input_data: TranscriptionData,
        context: ExecutionContext,
    ) -> EmbeddingCollection:
        output_path = self._get_output_path(input_data, context)

        if self._should_skip_processing(output_path, context, input_data):
            return self._load_cached_result(output_path, input_data)

        segments = self._load_and_validate_segments(input_data, context)
        if not segments:
            return self._create_embedding_collection(input_data, output_path, 0)

        self._ensure_model_loaded()
        context.logger.info(f'Generating text embeddings for {input_data.episode_id}')
        context.mark_step_started(self.name, input_data.episode_id)

        results = self._generate_embeddings(segments)
        self._save_results(results, output_path, input_data)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self._create_embedding_collection(input_data, output_path, len(results))

    @property
    def name(self) -> str:
        return 'text_embedding'

    @staticmethod
    def _get_output_path(input_data: TranscriptionData, context: ExecutionContext) -> Path:
        episode_code = input_data.episode_info.episode_code()
        output_filename: str = f'{context.series_name}_{episode_code}_embeddings_text.json'
        return context.get_output_path(input_data.episode_info, 'embeddings', output_filename)

    def _should_skip_processing(
        self,
        output_path: Path,
        context: ExecutionContext,
        input_data: TranscriptionData,
    ) -> bool:
        return self._check_cache_validity(
            output_path,
            context,
            input_data.episode_id,
            'cached text embeddings',
        )

    def _load_cached_result(  # pylint: disable=duplicate-code
        self,
        output_path: Path,
        input_data: TranscriptionData,
    ) -> EmbeddingCollection:
        emb_data: Dict[str, Any] = load_json(output_path)
        return self._create_embedding_collection(
            input_data,
            output_path,
            len(emb_data.get('results', [])),
        )

    def _load_and_validate_segments(
        self,
        input_data: TranscriptionData,
        context: ExecutionContext,
    ) -> List[Dict[str, Any]]:
        transcription: Dict[str, Any] = self.__load_clean_transcription(input_data, context)
        segments: List[Dict[str, Any]] = transcription.get('segments', [])
        if not segments:
            context.logger.warning(f'No text segments for embedding in {input_data.episode_id}')
        return segments

    def _ensure_model_loaded(self) -> None:
        if self._model is None:
            self._model = EmbeddingModelWrapper(
                self.config.model_name,
                self.config.device,
                self.config.batch_size,
            )

    def _generate_embeddings(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        full_text: str = ' '.join([seg.get('text', '') for seg in segments])
        sentences: List[str] = self.__split_into_sentences(full_text)
        text_chunks, chunk_metadata = self._create_text_chunks(sentences, segments)
        return self._batch_encode_chunks(text_chunks, chunk_metadata)

    def _create_text_chunks(
        self,
        sentences: List[str],
        segments: List[Dict[str, Any]],
    ) -> tuple[List[str], List[Dict[str, Any]]]:
        text_chunks: List[str] = []
        chunk_metadata: List[Dict[str, Any]] = []
        step: int = self.config.text_sentences_per_chunk - self.config.text_chunk_overlap

        for i in range(0, len(sentences), step):
            chunk_sentences: List[str] = sentences[i:i + self.config.text_sentences_per_chunk]
            if not chunk_sentences:
                continue

            chunk_text: str = ' '.join(chunk_sentences).strip()
            if not chunk_text:
                continue

            char_start: int = sum((len(s) + 1 for s in sentences[:i]))
            char_end: int = char_start + len(chunk_text)
            start_seg_id: int = self.__find_segment_at_position(segments, char_start)
            end_seg_id: int = self.__find_segment_at_position(segments, char_end)

            text_chunks.append(chunk_text)
            chunk_metadata.append({
                'segment_range': [start_seg_id, end_seg_id],
                'text': chunk_text,
            })

        return text_chunks, chunk_metadata

    def _batch_encode_chunks(
        self,
        text_chunks: List[str],
        chunk_metadata: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for i in range(0, len(text_chunks), self.config.batch_size):
            batch_texts: List[str] = text_chunks[i:i + self.config.batch_size]
            batch_meta: List[Dict[str, Any]] = chunk_metadata[i:i + self.config.batch_size]
            batch_embeddings: List[List[float]] = self._model.encode_text(batch_texts)

            for meta, emb in zip(batch_meta, batch_embeddings):
                results.append({**meta, 'embedding': emb})

        return results

    def _save_results(
        self,
        results: List[Dict[str, Any]],
        output_path: Path,
        input_data: TranscriptionData,
    ) -> None:
        output_data: Dict[str, Any] = MetadataBuilder.create_processing_metadata(
            episode_info=input_data.episode_info,
            processing_params=self.config.dict(),
            statistics={
                'total_embeddings': len(results),
                'embedding_dimension': len(results[0]['embedding']) if results else 0,
            },
            results_key='text_embeddings',
            results_data=results,
        )
        atomic_write_json(output_path, output_data)

    def _create_embedding_collection(  # pylint: disable=duplicate-code
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
            embedding_type='text',
        )

    @staticmethod
    def __find_segment_at_position(segments: List[Dict[str, Any]], char_pos: int) -> int:
        cumulative_length: int = 0
        for idx, seg in enumerate(segments):
            seg_length: int = len(seg.get('text', '')) + 1
            if cumulative_length <= char_pos < cumulative_length + seg_length:
                return idx
            cumulative_length += seg_length
        return len(segments) - 1 if segments else 0

    @staticmethod
    def __load_clean_transcription(
        input_data: TranscriptionData,
        context: ExecutionContext,  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        raw_path: Path = input_data.path
        clean_path: Path = (
            raw_path.parent.parent / 'clean' /
            raw_path.name.replace('.json', '_clean_transcription.json')
        )
        if clean_path.exists():
            return load_json(clean_path)
        return load_json(raw_path)

    @staticmethod
    def __split_into_sentences(text: str) -> List[str]:
        normalized_text: str = re.sub('\\.{2,}', '.', text)
        sentences: List[str] = re.split('([.!?]+(?:\\s+|$))', normalized_text)
        result: List[str] = []
        for i in range(0, len(sentences) - 1, 2):
            s: str = (sentences[i] + sentences[i + 1]).strip()
            if s:
                result.append(s)
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1].strip())
        return result
