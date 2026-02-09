import gc
import logging
from pathlib import Path
from typing import (
    List,
    Optional,
)

import torch

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.path_manager import PathManager
from preprocessor.utils.batch_processing_utils import compute_hashes_in_batches
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.utils.hash_save_utils import save_image_hashes_to_json
from preprocessor.utils.image_hasher import PerceptualHasher
from preprocessor.video.frame_processor import FrameSubProcessor

# pylint: disable=duplicate-code


class ImageHashSubProcessor(FrameSubProcessor):
    def __init__(self, device: str, batch_size: int):
        super().__init__("Image Hashing")
        self.device = device
        self.batch_size = batch_size
        self.hasher: Optional[PerceptualHasher] = None
        self.logger = ErrorHandlingLogger("ImageHashSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        if self.hasher is None:
            self.hasher = PerceptualHasher(device=self.device, hash_size=8)

    def cleanup(self) -> None:
        self.hasher = None
        self.__cleanup_memory()

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.image_hashes)
        series_name = item.metadata["series_name"]
        path_manager = PathManager(series_name)
        hash_filename = path_manager.build_filename(
            episode_info,
            extension="json",
            suffix="image_hashes",
        )
        hash_output = episode_dir / hash_filename
        return [OutputSpec(path=hash_output, required=True)]

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:
        self.initialize()

        metadata_file = item.input_path
        episode_info = item.metadata["episode_info"]

        frame_requests = self._load_frame_requests_from_metadata(metadata_file)
        if frame_requests is None:
            return

        hash_results = compute_hashes_in_batches(ramdisk_frames_dir, frame_requests, self.hasher, self.batch_size)
        series_name = item.metadata["series_name"]

        output_path = save_image_hashes_to_json(
            episode_info=episode_info,
            hash_results=hash_results,
            series_name=series_name,
            device=self.device,
            batch_size=self.batch_size,
        )
        console.print(f"[green]✓ Saved hashes to: {output_path}[/green]")

    @staticmethod
    def __cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
