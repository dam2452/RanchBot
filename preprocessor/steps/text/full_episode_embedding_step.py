# pylint: disable=duplicate-code
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import numpy as np

from preprocessor.config.step_configs import FullEpisodeEmbeddingConfig
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


class FullEpisodeEmbeddingStep(
    PipelineStep[TranscriptionData, EmbeddingCollection, FullEpisodeEmbeddingConfig],
):
    def __init__(self, config: FullEpisodeEmbeddingConfig) -> None:
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
                1,
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

        full_text = self.__build_full_text(input_data, context)
        if not full_text:
            return self.__build_collection(input_data, output_path, 0)

        self.__ensure_model()
        context.logger.info(f'Generating full episode embedding for {input_data.episode_id}')

        embedding = self.__embed_full_text(full_text)
        self.__save_result(embedding, full_text, output_path, input_data)

        return self.__build_collection(input_data, output_path, 1)

    def get_output_descriptors(self) -> List[FileOutput]:
        return [
            FileOutput(
                pattern="{season}/{episode}.json",
                subdir="embeddings/full_episode",
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
        count = 1 if data.get('full_episode_embedding') else 0
        return self.__build_collection(input_data, cache_path, count)

    def __ensure_model(self) -> None:
        if self.__model is None:
            self.__model = EmbeddingModelWrapper(
                self.config.model_name,
                self.config.device,
                1,
            )

    def __embed_full_text(self, full_text: str) -> List[float]:
        if len(full_text) <= self.config.max_chars_per_chunk:
            embedding: List[float] = self.__model.encode_text(full_text)  # type: ignore[assignment,union-attr]
            return embedding
        return self.__sliding_window_embed(full_text)

    def __sliding_window_embed(self, full_text: str) -> List[float]:
        chunks, weights = self.__build_chunks_and_weights(full_text)
        if not self.__model:
            raise RuntimeError("Embedding model not initialized")

        embeddings: List[List[float]] = self.__model.encode_text(chunks)  # type: ignore[assignment]
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        dim = len(embeddings[0])
        avg: np.ndarray = np.zeros(dim, dtype=np.float64)
        for emb, w in zip(embeddings, normalized_weights):
            avg += np.array(emb, dtype=np.float64) * w

        norm = float(np.linalg.norm(avg))
        if norm > 0:
            avg /= norm

        return avg.tolist()

    def __build_chunks_and_weights(
        self,
        full_text: str,
    ) -> Tuple[List[str], List[float]]:
        chunks: List[str] = []
        weights: List[float] = []
        step = self.config.max_chars_per_chunk - self.config.overlap_chars
        pos = 0

        while pos < len(full_text):
            chunk = full_text[pos : pos + self.config.max_chars_per_chunk]
            if len(chunk) >= self.config.min_chunk_length:
                chunks.append(chunk)
                weights.append(len(chunk) / self.config.max_chars_per_chunk)
            pos += step

        return chunks, weights

    def __save_result(
        self,
        embedding: List[float],
        full_text: str,
        output_path: Path,
        input_data: TranscriptionData,
    ) -> None:
        output_data: Dict[str, Any] = {
            'generated_at': datetime.now().isoformat(),
            'episode_info': {
                'season': input_data.episode_info.season,
                'episode_number': input_data.episode_info.relative_episode,
            },
            'processing_parameters': self.config.model_dump(),
            'statistics': {
                'transcript_length': len(full_text),
                'embedding_dimension': len(embedding),
            },
            'full_episode_embedding': {
                'text': full_text,
                'embedding': embedding,
                'transcript_length': len(full_text),
            },
        }
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
            embedding_type='full_episode',
        )

    @staticmethod
    def __create_path_vars(input_data: TranscriptionData) -> Dict[str, str]:
        return {
            "season": f"S{input_data.episode_info.season:02d}",
            "episode": input_data.episode_info.episode_code(),
        }

    @staticmethod
    def __build_full_text(
        input_data: TranscriptionData,
        context: ExecutionContext,
    ) -> str:
        data: Dict[str, Any] = FileOperations.load_json(input_data.path)
        segments: List[Dict[str, Any]] = data.get('segments', [])
        if not segments:
            context.logger.warning(
                f'No text segments for full episode embedding in {input_data.episode_id}',
            )
            return ''
        return ' '.join(s.get('text', '') for s in segments).strip()
