# pylint: disable=duplicate-code
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from preprocessor.config.step_configs import TextEmbeddingConfig
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


class TextEmbeddingStep(PipelineStep[TranscriptionData, EmbeddingCollection, TextEmbeddingConfig]):
    def __init__(self, config: TextEmbeddingConfig) -> None:
        super().__init__(config)
        self.__model: Optional[EmbeddingModelWrapper] = None

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__model is None:
            context.logger.info(f'Loading VLLM embedding model: {self.config.model_name}')
            self.__model = EmbeddingModelWrapper(
                self.config.model_name,
                self.config.device,
                self.config.batch_size,
            )

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__model:
            self.__model = None
            context.logger.info('VLLM embedding model unloaded')

    def cleanup(self) -> None:
        if self.__model:
            self.__model = None

    def execute_batch(
        self, input_data: List[TranscriptionData], context: ExecutionContext,
    ) -> List[EmbeddingCollection]:
        return self._execute_sequential(input_data, context, self.execute)

    def _process(
        self, input_data: TranscriptionData, context: ExecutionContext,
    ) -> EmbeddingCollection:
        output_path = self._get_cache_path(input_data, context)

        segments = self.__extract_valid_segments(input_data, context)
        if not segments:
            return self.__construct_embedding_collection(
                input_data, output_path, 0,
            )

        self.__prepare_embedding_model()
        context.logger.info(f'Generating text embeddings for {input_data.episode_id}')

        results = self.__process_text_embeddings(segments)
        self.__save_embedding_results(results, output_path, input_data)

        return self.__construct_embedding_collection(
            input_data, output_path, len(results),
        )

    def get_output_descriptors(self) -> List[FileOutput]:
        return [
            FileOutput(
                pattern="{season}/{episode}.json",
                subdir="embeddings/text",
                min_size_bytes=1024,
            ),
        ]

    def _get_cache_path(
        self, input_data: TranscriptionData, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            self.__create_path_variables(input_data),
        )

    def _load_from_cache(
        self, cache_path: Path, input_data: TranscriptionData, context: ExecutionContext,
    ) -> EmbeddingCollection:
        emb_data: Dict[str, Any] = FileOperations.load_json(cache_path)
        return self.__construct_embedding_collection(
            input_data,
            cache_path,
            len(emb_data.get('text_embeddings', [])),
        )

    def __prepare_embedding_model(self) -> None:
        if self.__model is None:
            self.__model = EmbeddingModelWrapper(
                self.config.model_name,
                self.config.device,
                self.config.batch_size,
            )

    def __process_text_embeddings(
        self, segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        full_text: str = ' '.join([seg.get('text', '') for seg in segments])
        sentences: List[str] = self.__split_into_sentences(full_text)
        text_chunks, chunk_metadata = self.__create_text_chunks(sentences, segments)
        return self.__batch_encode_chunks(text_chunks, chunk_metadata)

    def __create_text_chunks(
        self,
        sentences: List[str],
        segments: List[Dict[str, Any]],
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        text_chunks: List[str] = []
        chunk_metadata: List[Dict[str, Any]] = []
        step: int = (
            self.config.text_sentences_per_chunk - self.config.text_chunk_overlap
        )

        for i in range(0, len(sentences), step):
            chunk_sentences: List[str] = sentences[
                i : i + self.config.text_sentences_per_chunk
            ]
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

    def __batch_encode_chunks(
        self,
        text_chunks: List[str],
        chunk_metadata: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        if not self.__model:
            raise RuntimeError("Embedding model not initialized")

        for i in range(0, len(text_chunks), self.config.batch_size):
            batch_texts: List[str] = text_chunks[i : i + self.config.batch_size]
            batch_meta: List[Dict[str, Any]] = chunk_metadata[
                i : i + self.config.batch_size
            ]
            batch_embeddings: List[List[float]] = self.__model.encode_text(batch_texts)

            for meta, embedding in zip(batch_meta, batch_embeddings):
                results.append({**meta, 'embedding': embedding})

        return results

    def __save_embedding_results(
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
            results_key='text_embeddings',
            results_data=results,
        )
        FileOperations.atomic_write_json(output_path, output_data)

    def __construct_embedding_collection(
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
    def __create_path_variables(input_data: TranscriptionData) -> Dict[str, str]:
        return {
            "season": f"S{input_data.episode_info.season:02d}",
            "episode": input_data.episode_info.episode_code(),
        }

    @staticmethod
    def __extract_valid_segments(
        input_data: TranscriptionData,
        context: ExecutionContext,
    ) -> List[Dict[str, Any]]:
        transcription: Dict[str, Any] = TextEmbeddingStep.__load_clean_transcription(
            input_data,
        )
        segments: List[Dict[str, Any]] = transcription.get('segments', [])
        if not segments:
            context.logger.warning(
                f'No text segments for embedding in {input_data.episode_id}',
            )
        return segments

    @staticmethod
    def __load_clean_transcription(input_data: TranscriptionData) -> Dict[str, Any]:
        raw_path: Path = input_data.path
        clean_path: Path = (
            raw_path.parent.parent
            / 'clean'
            / raw_path.name.replace('.json', '_clean_transcription.json')
        )
        if clean_path.exists():
            return FileOperations.load_json(clean_path)
        return FileOperations.load_json(raw_path)

    @staticmethod
    def __find_segment_at_position(
        segments: List[Dict[str, Any]], char_pos: int,
    ) -> int:
        cumulative_length: int = 0
        for idx, seg in enumerate(segments):
            seg_length: int = len(seg.get('text', '')) + 1
            if cumulative_length <= char_pos < cumulative_length + seg_length:
                return idx
            cumulative_length += seg_length
        return len(segments) - 1 if segments else 0

    @staticmethod
    def __split_into_sentences(text: str) -> List[str]:
        normalized_text: str = re.sub(r'\.{2,}', '.', text)
        normalized_text = re.sub(r'!{2,}', '!', normalized_text)
        normalized_text = re.sub(r'\?{2,}', '?', normalized_text)
        sentences: List[str] = re.split(r'([.!?]+(?:\s+|$))', normalized_text)
        raw: List[str] = []
        for i in range(0, len(sentences) - 1, 2):
            s: str = (sentences[i] + sentences[i + 1]).strip()
            if s:
                raw.append(s)
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            raw.append(sentences[-1].strip())
        result: List[str] = []
        for sentence in raw:
            if len(sentence) < 30 and result:
                result[-1] = result[-1] + ' ' + sentence
            else:
                result.append(sentence)
        return result
