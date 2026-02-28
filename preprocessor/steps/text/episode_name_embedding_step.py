# pylint: disable=duplicate-code
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.step_configs import EpisodeNameEmbeddingConfig
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


class EpisodeNameEmbeddingStep(
    PipelineStep[TranscriptionData, EmbeddingCollection, EpisodeNameEmbeddingConfig],
):
    def __init__(self, config: EpisodeNameEmbeddingConfig) -> None:
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

        title = input_data.episode_info.title
        if not title:
            context.logger.warning(
                f'No title for episode name embedding in {input_data.episode_id}',
            )
            return self.__build_collection(input_data, output_path, 0)

        self.__ensure_model()
        context.logger.info(f'Generating episode name embedding for {input_data.episode_id}')

        embedding: List[float] = self.__model.encode_text(title)  # type: ignore[assignment,union-attr]
        self.__save_result(embedding, title, output_path, input_data)

        return self.__build_collection(input_data, output_path, 1)

    def get_output_descriptors(self) -> List[FileOutput]:
        return [
            FileOutput(
                pattern="{season}/{episode}.json",
                subdir="embeddings/episode_names",
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
        count = 1 if data.get('title_embedding') else 0
        return self.__build_collection(input_data, cache_path, count)

    def __ensure_model(self) -> None:
        if self.__model is None:
            self.__model = EmbeddingModelWrapper(
                self.config.model_name,
                self.config.device,
                1,
            )

    def __save_result(
        self,
        embedding: List[float],
        title: str,
        output_path: Path,
        input_data: TranscriptionData,
    ) -> None:
        episode_info = input_data.episode_info
        output_data: Dict[str, Any] = {
            'generated_at': datetime.now().isoformat(),
            'processing_parameters': self.config.model_dump(),
            'episode_id': input_data.episode_id,
            'title': title,
            'title_embedding': embedding,
            'episode_metadata': {
                'season': episode_info.season,
                'episode_number': episode_info.relative_episode,
                'title': title,
                'premiere_date': episode_info.premiere_date,
                'series_name': episode_info.series_name,
                'viewership': episode_info.viewership,
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
            embedding_type='episode_name',
        )

    @staticmethod
    def __create_path_vars(input_data: TranscriptionData) -> Dict[str, str]:
        return {
            "season": f"S{input_data.episode_info.season:02d}",
            "episode": input_data.episode_info.episode_code(),
        }
