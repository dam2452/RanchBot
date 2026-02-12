# pylint: disable=cyclic-import  # False positive - config uses import-outside-toplevel
import gc
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import torch

from preprocessor.config.step_configs import ImageHashConfig
from preprocessor.core.artifacts import (
    FrameCollection,
    ImageHashCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.io.files import FileOperations
from preprocessor.services.video.frame_utils import FrameLoader
from preprocessor.services.video.image_hasher import PerceptualHasher


class ImageHashStep(PipelineStep[FrameCollection, ImageHashCollection, ImageHashConfig]):

    def __init__(self, config: ImageHashConfig) -> None:
        super().__init__(config)
        self._hasher: Optional[PerceptualHasher] = None

    def cleanup(self) -> None:
        self._hasher = None
        self.__cleanup_memory()

    def execute(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ImageHashCollection:
        output_path = self._get_output_path(input_data, context)

        if self._check_cache_validity(output_path, context, input_data.episode_id, 'cached'):
            return self._load_cached_result(output_path, input_data)

        frame_metadata, frame_requests = self._load_frame_metadata(input_data, context)
        if not frame_requests:
            return self._create_empty_result(output_path, input_data)

        self._ensure_hasher_loaded(context)
        context.logger.info(
            f'Computing hashes for {len(frame_requests)} frames in {input_data.episode_id}',
        )
        context.mark_step_started(self.name, input_data.episode_id)

        hash_results = self._compute_hashes(frame_requests, input_data)
        self._save_results(hash_results, output_path, input_data, context, frame_metadata)

        context.mark_step_completed(self.name, input_data.episode_id)
        self.__cleanup_memory()

        return ImageHashCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            hash_count=len(hash_results),
        )

    @property
    def name(self) -> str:
        return 'image_hashing'

    @staticmethod
    def _get_output_path(input_data: FrameCollection, context: ExecutionContext) -> Path:
        filename_base = f'{context.series_name}_{input_data.episode_info.episode_code()}'
        output_filename: str = f'{filename_base}_image_hashes.json'
        return context.get_output_path(input_data.episode_info, 'image_hashes', output_filename)


    @staticmethod
    def _load_cached_result(output_path: Path, input_data: FrameCollection) -> ImageHashCollection:
        hash_data: Dict[str, Any] = FileOperations.load_json(output_path)
        return ImageHashCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            hash_count=len(hash_data.get('hashes', [])),
        )

    @staticmethod
    def _load_frame_metadata(
        input_data: FrameCollection,
        context: ExecutionContext,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        frame_metadata: Dict[str, Any] = FileOperations.load_json(input_data.metadata_path)
        frame_requests: List[Dict[str, Any]] = frame_metadata.get('frames', [])
        if not frame_requests:
            context.logger.warning(f'No frames to hash for {input_data.episode_id}')
        return frame_metadata, frame_requests

    @staticmethod
    def _create_empty_result(
        output_path: Path,
        input_data: FrameCollection,
    ) -> ImageHashCollection:
        return ImageHashCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            hash_count=0,
        )

    def _ensure_hasher_loaded(self, context: ExecutionContext) -> None:
        if self._hasher is None:
            context.logger.info(f'Loading image hasher on {self.config.device}...')
            self._hasher = PerceptualHasher()

    def _compute_hashes(
        self,
        frame_requests: List[Dict[str, Any]],
        input_data: FrameCollection,
    ) -> List[Dict[str, Any]]:
        hash_results: List[Dict[str, Any]] = []
        batch_size: int = self.config.batch_size

        for i in range(0, len(frame_requests), batch_size):
            batch: List[Dict[str, Any]] = frame_requests[i:i + batch_size]
            pil_images = FrameLoader.load_from_requests(input_data.directory, batch)
            phashes: List[str] = self._hasher.compute_phash_batch(pil_images)  # pylint: disable=no-member

            for request, phash in zip(batch, phashes):
                result: Dict[str, Any] = request.copy()
                result['perceptual_hash'] = phash
                hash_results.append(result)

            del pil_images
            if i % (batch_size * 5) == 0:
                self.__cleanup_memory()

        return hash_results

    @staticmethod
    def _save_results(
        hash_results: List[Dict[str, Any]],
        output_path: Path,
        input_data: FrameCollection,
        context: ExecutionContext,
        frame_metadata: Dict[str, Any],
    ) -> None:
        output_data: Dict[str, Any] = {
            'episode_id': input_data.episode_id,
            'series_name': context.series_name,
            'generated_at': frame_metadata.get('generated_at'),
            'hash_settings': {
                'device': 'cpu',
                'batch_size': len(hash_results) // 10 if hash_results else 1,
            },
            'hashes': hash_results,
        }
        FileOperations.atomic_write_json(output_path, output_data)

    @staticmethod
    def __cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
