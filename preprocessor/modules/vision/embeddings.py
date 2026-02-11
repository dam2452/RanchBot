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
from preprocessor.lib.io.files import (
    atomic_write_json,
    load_json,
)
from preprocessor.lib.io.metadata import MetadataBuilder
from preprocessor.lib.search.embedding_model import EmbeddingModelWrapper


class VideoEmbeddingStep(PipelineStep[FrameCollection, EmbeddingCollection, VideoEmbeddingConfig]):

    def __init__(self, config: VideoEmbeddingConfig) -> None:
        super().__init__(config)
        self._model: Optional[EmbeddingModelWrapper] = None

    @property
    def name(self) -> str:
        return 'video_embedding'

    def _create_embedding_collection(  # pylint: disable=duplicate-code
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

    def execute(  # pylint: disable=too-many-locals
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> EmbeddingCollection:
        filename_base = f'{context.series_name}_{input_data.episode_info.episode_code()}'
        output_filename: str = f'{filename_base}_embeddings_video.json'
        output_path: Path = context.get_output_path(input_data.episode_info, 'embeddings', output_filename)
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached video embeddings)')
                emb_data: Dict[str, Any] = load_json(output_path)
                return self._create_embedding_collection(
                    input_data,
                    output_path,
                    len(emb_data.get('video_embeddings', [])),
                )
        frame_metadata: Dict[str, Any] = load_json(input_data.metadata_path)
        frame_requests: List[Dict[str, Any]] = frame_metadata.get('frames', [])
        if not frame_requests:
            context.logger.warning(f'No frames for embedding in {input_data.episode_id}')
            return self._create_embedding_collection(input_data, output_path, 0)
        image_hashes: Dict[int, str] = self.__load_image_hashes(input_data, context)
        if self._model is None:
            self._model = EmbeddingModelWrapper(self.config.model_name, self.config.device)
            self._model.load_model()  # pylint: disable=no-member
        msg = (
            f'Generating video embeddings for {len(frame_requests)} frames '
            f'in {input_data.episode_id}'
        )
        context.logger.info(msg)
        context.mark_step_started(self.name, input_data.episode_id)
        results: List[Dict[str, Any]] = []
        batch_size: int = self.config.batch_size
        for i in range(0, len(frame_requests), batch_size):
            batch: List[Dict[str, Any]] = frame_requests[i:i + batch_size]
            image_paths: List[str] = [str(input_data.directory / f['frame_path']) for f in batch]
            batch_embeddings: List[np.ndarray] = self._model.encode_images(image_paths)  # pylint: disable=no-member
            for request, emb in zip(batch, batch_embeddings):
                res: Dict[str, Any] = {**request, 'embedding': emb.tolist()}
                frame_num: int = request.get('frame_number', -1)
                if frame_num in image_hashes:
                    res['perceptual_hash'] = image_hashes[frame_num]
                results.append(res)
        statistics = {
            'total_embeddings': len(results),
            'embedding_dimension': len(results[0]['embedding']) if results else 0,
            'frames_with_hash': len(image_hashes),
        }
        output_data: Dict[str, Any] = MetadataBuilder.create_processing_metadata(
            episode_info=input_data.episode_info,
            processing_params=self.config.dict(),
            statistics=statistics,
            results_key='video_embeddings',
            results_data=results,
        )
        atomic_write_json(output_path, output_data)
        context.mark_step_completed(self.name, input_data.episode_id)
        return self._create_embedding_collection(input_data, output_path, len(results))

    @staticmethod
    def __load_image_hashes(
        input_data: FrameCollection, context: ExecutionContext,
    ) -> Dict[int, str]:
        filename_base = f'{context.series_name}_{input_data.episode_info.episode_code()}'
        hash_filename: str = f'{filename_base}_image_hashes.json'
        hash_path: Path = context.get_output_path(input_data.episode_info, 'image_hashes', hash_filename)
        if not hash_path.exists():
            return {}
        try:
            data: Dict[str, Any] = load_json(hash_path)
            return {h['frame_number']: h['perceptual_hash'] for h in data.get('hashes', [])}
        except Exception as e:
            context.logger.warning(f'Could not load image hashes from {hash_path}: {e}')
            return {}

    def cleanup(self) -> None:
        if self._model:
            self._model.cleanup()  # pylint: disable=no-member
            self._model = None
