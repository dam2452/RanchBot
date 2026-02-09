import gc
import json
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
from preprocessor.embeddings.gpu_batch_processor import GPUBatchProcessor
from preprocessor.utils.batch_processing_utils import compute_embeddings_in_batches
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.utils.file_utils import atomic_write_json
from preprocessor.utils.image_hash_utils import load_image_hashes_for_episode
from preprocessor.utils.metadata_utils import create_processing_metadata
from preprocessor.video.frame_processor import FrameSubProcessor


class VideoEmbeddingSubProcessor(FrameSubProcessor):
    def __init__(self, device: str, batch_size: int, model_name: str, model_revision: str):
        super().__init__("Video Embeddings")
        self.device = device
        self.batch_size = batch_size
        self.model_name = model_name
        self.model_revision = model_revision
        self.model = None
        self.gpu_processor: Optional[GPUBatchProcessor] = None
        self.logger = ErrorHandlingLogger("VideoEmbeddingSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        if self.model is None:
            from preprocessor.embeddings.qwen3_vl_embedding import Qwen3VLEmbedder  # pylint: disable=import-outside-toplevel
            console.print(f"[cyan]Loading embedding model: {self.model_name}[/cyan]")
            self.model = Qwen3VLEmbedder(
                model_name_or_path=self.model_name,
                torch_dtype=torch.bfloat16,
            )
            self.gpu_processor = GPUBatchProcessor(
                self.model,
                self.batch_size,
                self.logger,
                self.device,
                progress_sub_batch_size=settings.embedding.progress_sub_batch_size,
            )
            console.print("[green]✓ Qwen3-VL-Embedding model loaded[/green]")

    def cleanup(self) -> None:
        self.model = None
        self.gpu_processor = None
        self.__cleanup_memory()

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.embeddings)
        series_name = item.metadata["series_name"]
        path_manager = PathManager(series_name)
        video_filename = path_manager.build_filename(
            episode_info,
            extension="json",
            suffix="embeddings_video",
        )
        video_output = episode_dir / video_filename
        return [OutputSpec(path=video_output, required=True)]

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

        episode_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.embeddings)
        checkpoint_file = episode_dir / "embeddings_video_checkpoint.json"

        series_name = item.metadata.get("series_name", "unknown")
        image_hashes = load_image_hashes_for_episode(
            {"season": episode_info.season, "episode_number": episode_info.relative_episode},
            series_name,
            self.logger,
        )
        video_embeddings = compute_embeddings_in_batches(
            ramdisk_frames_dir,
            frame_requests,
            self.gpu_processor,
            self.batch_size,
            image_hashes,
            checkpoint_file=checkpoint_file,
            checkpoint_interval=20,
            prefetch_count=settings.embedding.prefetch_chunks,
        )
        series_name = item.metadata["series_name"]
        self.__save_embeddings(episode_info, video_embeddings, series_name)

    def __save_embeddings(self, episode_info, video_embeddings: List[Dict[str, Any]], series_name: str) -> None:
        episode_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.embeddings)
        episode_dir.mkdir(parents=True, exist_ok=True)

        video_data = create_processing_metadata(
            episode_info=episode_info,
            processing_params={
                "model_name": self.model_name,
                "model_revision": self.model_revision,
                "batch_size": self.batch_size,
                "device": self.device,
            },
            statistics={
                "total_embeddings": len(video_embeddings),
                "embedding_dimension": len(video_embeddings[0]["embedding"]) if video_embeddings else 0,
                "frames_with_hash": sum(1 for e in video_embeddings if "perceptual_hash" in e),
            },
            results_key="video_embeddings",
            results_data=video_embeddings,
        )
        path_manager = PathManager(series_name)
        video_filename = path_manager.build_filename(
            episode_info,
            extension="json",
            suffix="embeddings_video",
        )
        video_output = episode_dir / video_filename
        atomic_write_json(video_output, video_data, indent=2, ensure_ascii=False)

        console.print(f"[green]✓ Saved embeddings to: {video_output}[/green]")

    @staticmethod
    def __cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
