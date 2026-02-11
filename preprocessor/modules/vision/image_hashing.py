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
from preprocessor.lib.io.files import (
    atomic_write_json,
    load_json,
)
from preprocessor.lib.video.frame_utils import FrameLoader
from preprocessor.lib.video.image_hasher import PerceptualHasher


class ImageHashStep(PipelineStep[FrameCollection, ImageHashCollection, ImageHashConfig]):

    def __init__(self, config: ImageHashConfig) -> None:
        super().__init__(config)
        self._hasher: Optional[PerceptualHasher] = None

    @property
    def name(self) -> str:
        return 'image_hashing'

    def execute(  # pylint: disable=too-many-locals
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ImageHashCollection:
        filename_base = f'{context.series_name}_{input_data.episode_info.episode_code()}'
        output_filename: str = f'{filename_base}_image_hashes.json'
        output_path: Path = context.get_output_path(input_data.episode_info, 'image_hashes', output_filename)
        if output_path.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached)')
                hash_data: Dict[str, Any] = load_json(output_path)
                return ImageHashCollection(
                    episode_id=input_data.episode_id,
                    episode_info=input_data.episode_info,
                    path=output_path,
                    hash_count=len(hash_data.get('hashes', [])),
                )
        frame_metadata: Dict[str, Any] = load_json(input_data.metadata_path)
        frame_requests: List[Dict[str, Any]] = frame_metadata.get('frames', [])
        if not frame_requests:
            context.logger.warning(f'No frames to hash for {input_data.episode_id}')
            return ImageHashCollection(
                episode_id=input_data.episode_id,
                episode_info=input_data.episode_info,
                path=output_path,
                hash_count=0,
            )
        if self._hasher is None:
            context.logger.info(f'Loading image hasher on {self.config.device}...')
            self._hasher = PerceptualHasher()
        msg = (
            f'Computing hashes for {len(frame_requests)} frames '
            f'in {input_data.episode_id}'
        )
        context.logger.info(msg)
        context.mark_step_started(self.name, input_data.episode_id)
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
        output_data: Dict[str, Any] = {
            'episode_id': input_data.episode_id,
            'series_name': context.series_name,
            'generated_at': frame_metadata.get('generated_at'),
            'hash_settings': {
                'device': self.config.device,
                'batch_size': self.config.batch_size,
            },
            'hashes': hash_results,
        }
        atomic_write_json(output_path, output_data)
        context.mark_step_completed(self.name, input_data.episode_id)
        self.__cleanup_memory()
        return ImageHashCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            hash_count=len(hash_results),
        )

    def cleanup(self) -> None:
        self._hasher = None
        self.__cleanup_memory()

    @staticmethod
    def __cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
