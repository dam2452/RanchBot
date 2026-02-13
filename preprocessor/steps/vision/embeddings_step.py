from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import numpy as np

from preprocessor.config.step_configs import VideoEmbeddingConfig
from preprocessor.core.artifacts import (
    EmbeddingCollection,
    FrameCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.io.files import FileOperations
from preprocessor.services.io.metadata import MetadataBuilder
from preprocessor.services.search.embedding_model import EmbeddingModelWrapper


class VideoEmbeddingStep(PipelineStep[FrameCollection, EmbeddingCollection, VideoEmbeddingConfig]):
    def __init__(self, config: VideoEmbeddingConfig) -> None:
        super().__init__(config)
        self.__model: Optional[EmbeddingModelWrapper] = None

    @property
    def name(self) -> str:
        return 'video_embedding'

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__model is None:
            context.logger.info(f'Loading VLLM embedding model: {self.config.model_name}')
            self.__model = EmbeddingModelWrapper(self.config.model_name, self.config.device)
            self.__model.load_model()

    def execute_batch(
        self, input_data: List[FrameCollection], context: ExecutionContext,
    ) -> List[EmbeddingCollection]:
        return self._execute_sequential(input_data, context, self.__execute_single)

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__model:
            self.__model.cleanup()
            self.__model = None
            context.logger.info('VLLM embedding model unloaded')

    def cleanup(self) -> None:
        if self.__model:
            self.__model.cleanup()
            self.__model = None

    def execute(
            self, input_data: FrameCollection, context: ExecutionContext,
    ) -> EmbeddingCollection:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached video embeddings'):
            return self.__load_cached_result(output_path, input_data)

        frame_requests = self.__extract_frame_requests(input_data, context)
        if not frame_requests:
            return self.__construct_embedding_collection(input_data, output_path, 0)

        self.__prepare_embedding_model(context)
        context.logger.info(
            f'Generating video embeddings for {len(frame_requests)} frames in {input_data.episode_id}',
        )
        context.mark_step_started(self.name, input_data.episode_id)

        image_hashes = self.__fetch_image_hashes(input_data, context)
        results = self.__generate_embeddings(frame_requests, input_data, image_hashes)
        self.__save_embedding_results(results, output_path, input_data, image_hashes)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_embedding_collection(input_data, output_path, len(results))

    def __execute_single(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> EmbeddingCollection:
        output_path = self.__resolve_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached video embeddings'):
            return self.__load_cached_result(output_path, input_data)

        frame_requests = self.__extract_frame_requests(input_data, context)
        if not frame_requests:
            return self.__construct_embedding_collection(input_data, output_path, 0)

        context.logger.info(
            f'Generating video embeddings for {len(frame_requests)} frames in {input_data.episode_id}',
        )
        context.mark_step_started(self.name, input_data.episode_id)

        image_hashes = self.__fetch_image_hashes(input_data, context)
        results = self.__generate_embeddings(frame_requests, input_data, image_hashes)
        self.__save_embedding_results(results, output_path, input_data, image_hashes)

        context.mark_step_completed(self.name, input_data.episode_id)
        return self.__construct_embedding_collection(input_data, output_path, len(results))

    def __prepare_embedding_model(self, context: ExecutionContext) -> None:
        if self.__model is None:
            context.logger.info('Initializing embedding model...')
            self.__model = EmbeddingModelWrapper(self.config.model_name, self.config.device)
            self.__model.load_model()

    def __generate_embeddings(
            self,
            frame_requests: List[Dict[str, Any]],
            input_data: FrameCollection,
            image_hashes: Dict[int, str],
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        batch_size: int = self.config.batch_size

        for i in range(0, len(frame_requests), batch_size):
            batch: List[Dict[str, Any]] = frame_requests[i:i + batch_size]
            image_paths: List[str] = [str(input_data.directory / f['frame_path']) for f in batch]
            batch_embeddings: List[np.ndarray] = self.__model.encode_images(image_paths)

            for request, embedding in zip(batch, batch_embeddings):
                res: Dict[str, Any] = {**request, 'embedding': embedding.tolist()}
                frame_num: int = request.get('frame_number', -1)
                if frame_num in image_hashes:
                    res['perceptual_hash'] = image_hashes[frame_num]
                results.append(res)

        return results

    def __load_cached_result(
            self,
            output_path: Path,
            input_data: FrameCollection,
    ) -> EmbeddingCollection:
        emb_data: Dict[str, Any] = FileOperations.load_json(output_path)
        return self.__construct_embedding_collection(
            input_data,
            output_path,
            len(emb_data.get('video_embeddings', [])),
        )

    def __construct_embedding_collection(  # pylint: disable=duplicate-code
            self,
            input_data: FrameCollection,
            output_path: Path,
            embedding_count: int,
    ) -> EmbeddingCollection:
        return MetadataBuilder.create_embedding_collection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            model_name=self.config.model_name,
            embedding_count=embedding_count,
            embedding_type='video',
        )

    @staticmethod
    def __save_embedding_results(
            results: List[Dict[str, Any]],
            output_path: Path,
            input_data: FrameCollection,
            image_hashes: Dict[int, str],
    ) -> None:
        statistics = {
            'total_embeddings': len(results),
            'embedding_dimension': len(results[0]['embedding']) if results else 0,
            'frames_with_hash': len(image_hashes),
        }
        output_data: Dict[str, Any] = MetadataBuilder.create_processing_metadata(
            episode_info=input_data.episode_info,
            processing_params={},
            statistics=statistics,
            results_key='video_embeddings',
            results_data=results,
        )
        FileOperations.atomic_write_json(output_path, output_data)

    @staticmethod
    def __resolve_output_path(input_data: FrameCollection, context: ExecutionContext) -> Path:
        filename_base = f'{context.series_name}_{input_data.episode_info.episode_code()}'
        output_filename: str = f'{filename_base}_embeddings_video.json'
        return context.get_output_path(input_data.episode_info, 'embeddings', output_filename)

    @staticmethod
    def __extract_frame_requests(
            input_data: FrameCollection,
            context: ExecutionContext,
    ) -> List[Dict[str, Any]]:
        frame_metadata: Dict[str, Any] = FileOperations.load_json(input_data.metadata_path)
        frame_requests: List[Dict[str, Any]] = frame_metadata.get('frames', [])
        if not frame_requests:
            context.logger.warning(f'No frames for embedding in {input_data.episode_id}')
        return frame_requests

    @staticmethod
    def __fetch_image_hashes(
            input_data: FrameCollection, context: ExecutionContext,
    ) -> Dict[int, str]:
        filename_base = f'{context.series_name}_{input_data.episode_info.episode_code()}'
        hash_filename: str = f'{filename_base}_image_hashes.json'
        hash_path: Path = context.get_output_path(input_data.episode_info, 'image_hashes', hash_filename)

        if not hash_path.exists():
            return {}

        try:
            data: Dict[str, Any] = FileOperations.load_json(hash_path)
            return {h['frame_number']: h['perceptual_hash'] for h in data.get('hashes', [])}
        except Exception as e:
            context.logger.warning(f'Could not load image hashes from {hash_path}: {e}')
            return {}
