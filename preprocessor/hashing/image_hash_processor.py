import gc
import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from PIL import Image
import torch

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.embeddings.image_hasher import PerceptualHasher
from preprocessor.utils.console import console


class ImageHashProcessor(BaseProcessor):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=11,
            loglevel=logging.DEBUG,
        )

        self.frames_dir: Path = Path(self._args.get("frames_dir", settings.frame_export.output_dir))
        self.output_dir: Path = Path(self._args.get("output_dir", settings.embedding.default_output_dir))
        self.batch_size: int = self._args.get("batch_size", settings.embedding.batch_size)
        self.device: str = "cuda"

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

        self.hasher: PerceptualHasher = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. This application requires GPU.")

    def cleanup(self) -> None:
        console.print("[cyan]Unloading image hasher...[/cyan]")
        self.hasher = None
        self._cleanup_memory()
        console.print("[green]✓ Hasher unloaded[/green]")

    def _get_processing_items(self) -> List[ProcessingItem]:
        all_metadata_files = list(self.frames_dir.glob("**/frame_metadata.json"))
        items = []

        for metadata_file in all_metadata_files:
            episode_info = self.episode_manager.parse_filename(metadata_file)
            if not episode_info:
                continue

            items.append(
                ProcessingItem(
                    input_path=metadata_file,
                    metadata={"episode_info": episode_info},
                )
            )

        return items

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        season = episode_info.season
        episode = episode_info.relative_episode
        episode_dir = self.output_dir / f"S{season:02d}" / f"E{episode:02d}"

        hash_output = episode_dir / "image_hashes.json"
        return [OutputSpec(path=hash_output, required=True)]

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
        hash_results = self.__compute_hashes(frames_dir, frame_requests)

        episode_dir = self.__get_episode_output_dir(episode_info)
        self.__save_hashes(episode_dir, episode_info, hash_results)
        self._cleanup_memory()

    def __compute_hashes(self, frames_dir: Path, frame_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        total_chunks = (len(frame_requests) + self.batch_size - 1) // self.batch_size
        results = []

        with self.progress.track_operation(f"Image hashing ({len(frame_requests)} frames)", total_chunks) as tracker:
            for chunk_idx in range(total_chunks):
                chunk_start = chunk_idx * self.batch_size
                chunk_end = min(chunk_start + self.batch_size, len(frame_requests))
                chunk_requests = frame_requests[chunk_start:chunk_end]

                pil_images = self.__load_frames(frames_dir, chunk_requests)
                phashes = self.hasher.compute_phash_batch(pil_images)

                for request, phash in zip(chunk_requests, phashes):
                    result = request.copy()
                    result["perceptual_hash"] = phash
                    results.append(result)

                del pil_images
                tracker.update(chunk_idx + 1, interval=10)

        return results

    @staticmethod
    def __load_frames(frames_dir: Path, frame_requests: List[Dict[str, Any]]) -> List[Image.Image]:
        images = []
        for request in frame_requests:
            frame_num = request["frame_number"]
            frame_path = frames_dir / f"frame_{frame_num:06d}.jpg"
            if frame_path.exists():
                images.append(Image.open(frame_path))
            else:
                images.append(Image.new('RGB', (1, 1)))
        return images

    def __get_episode_output_dir(self, episode_info) -> Path:
        season = episode_info.season
        episode = episode_info.relative_episode
        return self.output_dir / f"S{season:02d}" / f"E{episode:02d}"

    @staticmethod
    def __save_hashes(episode_dir: Path, episode_info, hash_results: List[Dict[str, Any]]) -> None:
        episode_dir.mkdir(parents=True, exist_ok=True)

        minimal_episode_info = {
            "season": episode_info.season,
            "episode_number": episode_info.relative_episode,
        }

        hash_data = {
            "episode_info": minimal_episode_info,
            "image_hashes": hash_results,
        }

        hash_output = episode_dir / "image_hashes.json"
        with open(hash_output, "w", encoding="utf-8") as f:
            json.dump(hash_data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
