import gc
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import torch

from preprocessor.config.step_configs import ImageHashConfig
from preprocessor.core.artifacts import (
    FrameCollection,
    ImageHashCollection,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import (
    JsonFileOutput,
    OutputDescriptor,
)
from preprocessor.services.io.files import FileOperations
from preprocessor.services.video.frame_utils import FrameLoader
from preprocessor.services.video.image_hasher import PerceptualHasher


class ImageHashStep(PipelineStep[FrameCollection, ImageHashCollection, ImageHashConfig]):
    def __init__(self, config: ImageHashConfig) -> None:
        super().__init__(config)
        self.__hasher: Optional[PerceptualHasher] = None

    @property
    def name(self) -> str:
        return 'image_hashing'

    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[FrameCollection], context: ExecutionContext,
    ) -> List[ImageHashCollection]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def cleanup(self) -> None:
        self.__hasher = None
        self.__cleanup_memory()

    def _process(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> ImageHashCollection:
        output_path = self._get_cache_path(input_data, context)

        frame_metadata, frame_requests = self.__load_frame_metadata(input_data, context)
        if not frame_requests:
            return self.__construct_empty_result(output_path, input_data)

        self.__prepare_hasher(context)

        context.logger.info(
            f'Computing hashes for {len(frame_requests)} frames in {input_data.episode_id}',
        )

        hash_results = self.__compute_hashes(frame_requests, input_data)
        self.__save_hash_results(
            hash_results, output_path, input_data, context, frame_metadata,
        )

        self.__cleanup_memory()

        return ImageHashCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            hash_count=len(hash_results),
        )

    def _get_output_descriptors(self) -> List[OutputDescriptor]:
        return [
            JsonFileOutput(
                subdir="hashes",
                pattern="{season}/{episode}.json",
                min_size_bytes=50,
            ),
        ]

    def _get_cache_path(
        self, input_data: FrameCollection, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            self.__create_path_variables(input_data),
        )

    def _load_from_cache(
        self, cache_path: Path, input_data: FrameCollection, context: ExecutionContext,
    ) -> ImageHashCollection:
        hash_data: Dict[str, Any] = FileOperations.load_json(cache_path)
        return ImageHashCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=cache_path,
            hash_count=len(hash_data.get('hashes', [])),
        )

    def __prepare_hasher(self, context: ExecutionContext) -> None:
        if self.__hasher is None:
            context.logger.info(f'Loading image hasher on {self.config.device}...')
            self.__hasher = PerceptualHasher()

    def __compute_hashes(
        self,
        frame_requests: List[Dict[str, Any]],
        input_data: FrameCollection,
    ) -> List[Dict[str, Any]]:
        hash_results: List[Dict[str, Any]] = []
        batch_size: int = self.config.batch_size

        for i in range(0, len(frame_requests), batch_size):
            batch: List[Dict[str, Any]] = frame_requests[i : i + batch_size]
            pil_images = FrameLoader.load_from_requests(input_data.directory, batch)
            phashes: List[str] = self.__hasher.compute_phash_batch(pil_images)

            for request, phash in zip(batch, phashes):
                result: Dict[str, Any] = request.copy()
                result['perceptual_hash'] = phash
                hash_results.append(result)

            del pil_images
            if i % (batch_size * 5) == 0:
                self.__cleanup_memory()

        return hash_results

    @staticmethod
    def __create_path_variables(input_data: FrameCollection) -> Dict[str, str]:
        return {
            'season': f'S{input_data.episode_info.season:02d}',
            'episode': input_data.episode_info.episode_code(),
        }

    @staticmethod
    def __load_frame_metadata(
        input_data: FrameCollection,
        context: ExecutionContext,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        frame_metadata: Dict[str, Any] = FileOperations.load_json(
            input_data.metadata_path,
        )
        frame_requests: List[Dict[str, Any]] = frame_metadata.get('frames', [])

        if not frame_requests:
            context.logger.warning(f'No frames to hash for {input_data.episode_id}')

        return frame_metadata, frame_requests

    @staticmethod
    def __construct_empty_result(
        output_path: Path,
        input_data: FrameCollection,
    ) -> ImageHashCollection:
        return ImageHashCollection(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=output_path,
            hash_count=0,
        )

    @staticmethod
    def __save_hash_results(
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
