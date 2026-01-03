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

from insightface.app import FaceAnalysis
import numpy as np
import torch
from transformers import AutoModel

from preprocessor.characters.face_detection_utils import load_character_references
from preprocessor.characters.utils import init_face_detection
from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    OutputSpec,
    ProcessingItem,
)
from preprocessor.embeddings.gpu_batch_processor import GPUBatchProcessor
from preprocessor.embeddings.image_hasher import PerceptualHasher
from preprocessor.utils.batch_processing_utils import (
    compute_embeddings_in_batches,
    compute_hashes_in_batches,
)
from preprocessor.utils.console import console
from preprocessor.utils.detection_io import (
    process_frames_for_detection,
    save_character_detections,
)
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.utils.image_hash_utils import load_image_hashes_for_episode
from preprocessor.utils.metadata_utils import create_processing_metadata
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
        self._cleanup_memory()

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        hash_output_dir = Path(settings.image_hash.output_dir)
        season = episode_info.season
        episode = episode_info.relative_episode
        hash_episode_dir = hash_output_dir / f"S{season:02d}" / f"E{episode:02d}"
        hash_output = hash_episode_dir / "image_hashes.json"
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
        self.__save_hashes(episode_info, hash_results)

    def __save_hashes(self, episode_info, hash_results: List[Dict[str, Any]]) -> None:
        hash_output_dir = Path(settings.image_hash.output_dir)
        season = episode_info.season
        episode = episode_info.relative_episode
        hash_episode_dir = hash_output_dir / f"S{season:02d}" / f"E{episode:02d}"
        hash_episode_dir.mkdir(parents=True, exist_ok=True)

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

        hash_output = hash_episode_dir / "image_hashes.json"
        with open(hash_output, "w", encoding="utf-8") as f:
            json.dump(hash_data, f, indent=2, ensure_ascii=False)

        console.print(f"[green]✓ Saved hashes to: {hash_output}[/green]")

    @staticmethod
    def _cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class VideoEmbeddingSubProcessor(FrameSubProcessor):
    def __init__(self, device: str, batch_size: int, model_name: str, model_revision: str, resize_height: int):
        super().__init__("Video Embeddings")
        self.device = device
        self.batch_size = batch_size
        self.model_name = model_name
        self.model_revision = model_revision
        self.resize_height = resize_height
        self.model = None
        self.gpu_processor: Optional[GPUBatchProcessor] = None
        self.logger = ErrorHandlingLogger("VideoEmbeddingSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        if self.model is None:
            console.print(f"[cyan]Loading GME model: {self.model_name}[/cyan]")
            self.model = AutoModel.from_pretrained(
                self.model_name,
                torch_dtype="float16",
                device_map="cuda",
                trust_remote_code=True,
            )
            self.model.eval()
            self.gpu_processor = GPUBatchProcessor(self.model, self.batch_size, self.logger, self.device)
            console.print("[green]✓ GME model loaded[/green]")

    def cleanup(self) -> None:
        self.model = None
        self.gpu_processor = None
        self._cleanup_memory()

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        embeddings_output_dir = Path(settings.embedding.default_output_dir)
        season = episode_info.season
        episode = episode_info.relative_episode
        embeddings_episode_dir = embeddings_output_dir / f"S{season:02d}" / f"E{episode:02d}"
        video_output = embeddings_episode_dir / "embeddings_video.json"
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

        image_hashes = load_image_hashes_for_episode(
            {"season": episode_info.season, "episode_number": episode_info.relative_episode},
            self.logger,
        )
        video_embeddings = compute_embeddings_in_batches(
            ramdisk_frames_dir,
            frame_requests,
            self.gpu_processor,
            self.batch_size,
            image_hashes,
        )
        self.__save_embeddings(episode_info, video_embeddings)

    def __save_embeddings(self, episode_info, video_embeddings: List[Dict[str, Any]]) -> None:
        embeddings_output_dir = Path(settings.embedding.default_output_dir)
        season = episode_info.season
        episode = episode_info.relative_episode
        embeddings_episode_dir = embeddings_output_dir / f"S{season:02d}" / f"E{episode:02d}"
        embeddings_episode_dir.mkdir(parents=True, exist_ok=True)

        video_data = create_processing_metadata(
            episode_info=episode_info,
            processing_params={
                "model_name": self.model_name,
                "model_revision": self.model_revision,
                "resize_height": self.resize_height,
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

        video_output = embeddings_episode_dir / "embeddings_video.json"
        with open(video_output, "w", encoding="utf-8") as f:
            json.dump(video_data, f, indent=2, ensure_ascii=False)

        console.print(f"[green]✓ Saved embeddings to: {video_output}[/green]")

    @staticmethod
    def _cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class CharacterDetectionSubProcessor(FrameSubProcessor):
    def __init__(self, characters_dir: Path, use_gpu: bool, threshold: float):
        super().__init__("Character Detection")
        self.characters_dir = characters_dir
        self.use_gpu = use_gpu
        self.threshold = threshold
        self.face_app: Optional[FaceAnalysis] = None
        self.character_vectors: Dict[str, np.ndarray] = {}
        self.logger = ErrorHandlingLogger("CharacterDetectionSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        if self.face_app is None:
            console.print("[cyan]Initializing face detection...[/cyan]")
            self.face_app = init_face_detection(self.use_gpu)
            self.character_vectors = load_character_references(self.characters_dir, self.face_app)
            console.print("[green]✓ Face detection initialized[/green]")

    def cleanup(self) -> None:
        self.face_app = None
        self.character_vectors = {}

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        detections_output_dir = Path(settings.character.detections_dir)
        season = episode_info.season
        episode = episode_info.relative_episode
        episode_dir = detections_output_dir / f"S{season:02d}" / f"E{episode:02d}"
        detections_output = episode_dir / "detections.json"
        return [OutputSpec(path=detections_output, required=True)]

    def should_run(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> bool:
        if not self.characters_dir.exists():
            console.print(f"[yellow]Characters directory not found: {self.characters_dir}, skipping[/yellow]")
            return False

        expected = self.get_expected_outputs(item)
        return any(str(exp.path) in str(miss.path) for exp in expected for miss in missing_outputs)

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:
        self.initialize()

        if not self.character_vectors:
            console.print("[yellow]No character references loaded, skipping detection[/yellow]")
            return

        episode_info = item.metadata["episode_info"]

        frame_files = sorted([
            f for f in ramdisk_frames_dir.glob("*.jpg")
            if f.is_file() and f.name.startswith("frame_")
        ])

        console.print(f"[cyan]Detecting characters in {len(frame_files)} frames[/cyan]")

        results = process_frames_for_detection(
            frame_files,
            self.face_app,
            self.character_vectors,
            self.threshold,
        )
        save_character_detections(episode_info, results)
