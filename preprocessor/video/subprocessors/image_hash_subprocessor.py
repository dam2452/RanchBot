import gc
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
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
from preprocessor.utils.image_hasher import PerceptualHasher
from preprocessor.utils.batch_processing_utils import compute_hashes_in_batches
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.utils.file_utils import atomic_write_json
from preprocessor.utils.metadata_utils import create_processing_metadata
from preprocessor.video.frame_processor import FrameSubProcessor
import json


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

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

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

    def should_run(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> bool:
        expected = self.get_expected_outputs(item)
        return any(str(exp.path) in str(miss.path) for exp in expected for miss in missing_outputs)

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:
        self.initialize()

        metadata_file = item.input_path
        episode_info = item.metadata["episode_info"]

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        frame_requests = metadata.get("frames", [])
        if not frame_requests:
            console.print(f"[yellow]No frames in metadata for {metadata_file}[/yellow]")
            return

        hash_results = compute_hashes_in_batches(ramdisk_frames_dir, frame_requests, self.hasher, self.batch_size)
        series_name = item.metadata["series_name"]
        self.__save_hashes(episode_info, hash_results, series_name)

    def __save_hashes(self, episode_info, hash_results: List[Dict[str, Any]], series_name: str) -> None:
        episode_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.image_hashes)
        episode_dir.mkdir(parents=True, exist_ok=True)

        hash_data = create_processing_metadata(
            episode_info=episode_info,
            processing_params={
                "device": self.device,
                "batch_size": self.batch_size,
                "hash_size": 8,
            },
            statistics={
                "total_hashes": len(hash_results),
                "unique_hashes": len(set(h.get("perceptual_hash") for h in hash_results if "perceptual_hash" in h)),
            },
            results_key="image_hashes",
            results_data=hash_results,
        )

        path_manager = PathManager(series_name)
        hash_filename = path_manager.build_filename(
            episode_info,
            extension="json",
            suffix="image_hashes",
        )
        hash_output = episode_dir / hash_filename
        atomic_write_json(hash_output, hash_data, indent=2, ensure_ascii=False)

        console.print(f"[green]✓ Saved hashes to: {hash_output}[/green]")

    @staticmethod
    def __cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
