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
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.embeddings.image_hasher import PerceptualHasher
from preprocessor.utils.batch_processing_utils import compute_hashes_in_batches
from preprocessor.utils.console import console
from preprocessor.utils.metadata_utils import create_processing_metadata

# pylint: disable=duplicate-code



class ImageHashProcessor(BaseProcessor):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=11,
            loglevel=logging.DEBUG,
        )

        self.frames_dir: Path = Path(self._args.get("frames_dir", settings.frame_export.output_dir))
        self.output_dir: Path = Path(self._args.get("output_dir", settings.image_hash.output_dir))
        self.batch_size: int = self._args.get("batch_size", settings.embedding.batch_size)
        self.device: str = "cuda"

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

        self.hasher: Optional[PerceptualHasher] = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. This application requires GPU.")

    def cleanup(self) -> None:
        console.print("[cyan]Unloading image hasher...[/cyan]")
        self.hasher = None
        self._cleanup_memory()
        console.print("[green]✓ Hasher unloaded[/green]")

    # pylint: disable=duplicate-code
    def _get_processing_items(self) -> List[ProcessingItem]:
        return self._get_episode_processing_items_from_metadata(
            "**/frame_metadata.json",
            self.frames_dir,
            self.episode_manager,
        )

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = self._build_episode_output_dir(episode_info, self.output_dir)
        hash_output = episode_dir / "image_hashes.json"
        return [OutputSpec(path=hash_output, required=True)]
    # pylint: enable=duplicate-code

    def _execute_processing(self, items: List[ProcessingItem]) -> None:
        console.print(f"[cyan]Device: {self.device}[/cyan]")
        console.print(f"[cyan]Batch size: {self.batch_size}[/cyan]")

        self.hasher = PerceptualHasher(device=self.device, hash_size=8)

        super()._execute_processing(items)
        console.print("[green]Image hashing completed[/green]")

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        metadata_file = item.input_path
        episode_info = item.metadata["episode_info"]

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        frame_requests = metadata.get("frames", [])
        if not frame_requests:
            console.print(f"[yellow]No frames in metadata for {metadata_file}[/yellow]")
            return

        frames_dir = metadata_file.parent
        hash_results = compute_hashes_in_batches(frames_dir, frame_requests, self.hasher, self.batch_size)

        episode_dir = self.__get_episode_output_dir(episode_info)
        self.__save_hashes(episode_dir, episode_info, hash_results)
        self._cleanup_memory()

    def __get_episode_output_dir(self, episode_info) -> Path:
        season = episode_info.season
        episode = episode_info.relative_episode
        return self.output_dir / f"S{season:02d}" / f"E{episode:02d}"

    def __save_hashes(self, episode_dir: Path, episode_info, hash_results: List[Dict[str, Any]]) -> None:
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

        hash_output = episode_dir / "image_hashes.json"
        with open(hash_output, "w", encoding="utf-8") as f:
            json.dump(hash_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
