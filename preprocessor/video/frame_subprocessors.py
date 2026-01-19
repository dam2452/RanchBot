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

from preprocessor.characters.face_detection_utils import load_character_references
from preprocessor.characters.utils import init_face_detection
from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.embeddings.gpu_batch_processor import GPUBatchProcessor
from preprocessor.hashing.image_hasher import PerceptualHasher
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
from preprocessor.utils.file_utils import atomic_write_json
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
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.image_hashes)
        hash_output = episode_dir / "image_hashes.json"
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
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.image_hashes)
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
        atomic_write_json(hash_output, hash_data, indent=2, ensure_ascii=False)

        console.print(f"[green]✓ Saved hashes to: {hash_output}[/green]")

    @staticmethod
    def _cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


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
        self._cleanup_memory()

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.embeddings)
        video_output = episode_dir / "embeddings_video.json"
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

        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.embeddings)
        checkpoint_file = episode_dir / "embeddings_video_checkpoint.json"

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
            checkpoint_file=checkpoint_file,
            checkpoint_interval=20,
            prefetch_count=settings.embedding.prefetch_chunks,
        )
        self.__save_embeddings(episode_info, video_embeddings)

    def __save_embeddings(self, episode_info, video_embeddings: List[Dict[str, Any]]) -> None:
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.embeddings)
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

        video_output = episode_dir / "embeddings_video.json"
        atomic_write_json(video_output, video_data, indent=2, ensure_ascii=False)

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
            self.face_app = init_face_detection()
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
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.character_detections)
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

        fps = 25.0

        results = process_frames_for_detection(
            frame_files,
            self.face_app,
            self.character_vectors,
            self.threshold,
            fps=fps,
        )
        save_character_detections(episode_info, results, fps=fps)


class ObjectDetectionSubProcessor(FrameSubProcessor):
    def __init__(self, model_name: str = "ustc-community/dfine-xlarge-obj2coco", conf_threshold: float = 0.25):
        super().__init__("Object Detection")
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.model: Optional[Any] = None
        self.image_processor: Optional[Any] = None
        self.logger = ErrorHandlingLogger("ObjectDetectionSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        if self.model is None:
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is not available. Object detection requires GPU.")

            from transformers import (  # pylint: disable=import-outside-toplevel
                AutoImageProcessor,
                DFineForObjectDetection,
            )

            console.print(f"[cyan]Loading D-FINE model: {self.model_name}[/cyan]")
            self.image_processor = AutoImageProcessor.from_pretrained(self.model_name)
            self.model = DFineForObjectDetection.from_pretrained(self.model_name)
            self.model.to("cuda")
            console.print("[green]✓ D-FINE model loaded on GPU[/green]")

    def cleanup(self) -> None:
        self.model = None
        self.image_processor = None
        self._cleanup_memory()

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.object_detections)
        detections_output = episode_dir / "detections.json"
        return [OutputSpec(path=detections_output, required=True)]

    def should_run(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> bool:
        expected = self.get_expected_outputs(item)
        return any(str(exp.path) in str(miss.path) for exp in expected for miss in missing_outputs)

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:  # pylint: disable=too-many-locals
        self.initialize()

        from PIL import Image  # pylint: disable=import-outside-toplevel

        episode_info = item.metadata["episode_info"]

        frame_files = sorted([
            f for f in ramdisk_frames_dir.glob("*.jpg")
            if f.is_file() and f.name.startswith("frame_")
        ])

        if not frame_files:
            console.print(f"[yellow]No frames found in {ramdisk_frames_dir}[/yellow]")
            return

        console.print(f"[cyan]Detecting objects in {len(frame_files)} frames[/cyan]")

        detections_data = {
            "episode_code": f"S{episode_info.season:02d}E{episode_info.relative_episode:02d}",
            "model": self.model_name,
            "confidence_threshold": self.conf_threshold,
            "frames": [],
        }

        batch_size = 8
        for batch_start in range(0, len(frame_files), batch_size):
            batch_paths = frame_files[batch_start:batch_start + batch_size]
            batch_images = [Image.open(fp) for fp in batch_paths]
            target_sizes = [(img.height, img.width) for img in batch_images]

            inputs = self.image_processor(images=batch_images, return_tensors="pt")
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)

            results = self.image_processor.post_process_object_detection(
                outputs,
                target_sizes=target_sizes,
                threshold=self.conf_threshold,
            )

            for frame_path, result in zip(batch_paths, results):
                frame_result = {
                    "frame_name": frame_path.name,
                    "detections": [],
                }

                for score, label_id, box in zip(result["scores"], result["labels"], result["boxes"]):
                    score_value = score.item()
                    label = label_id.item()
                    box_coords = [float(i) for i in box.tolist()]

                    detection = {
                        "class_id": label,
                        "class_name": self.model.config.id2label[label],
                        "confidence": score_value,
                        "bbox": {
                            "x1": box_coords[0],
                            "y1": box_coords[1],
                            "x2": box_coords[2],
                            "y2": box_coords[3],
                        },
                    }
                    frame_result["detections"].append(detection)

                frame_result["detection_count"] = len(frame_result["detections"])
                detections_data["frames"].append(frame_result)

            for img in batch_images:
                img.close()

        total_detections = sum(f['detection_count'] for f in detections_data['frames'])
        frames_with_detections = len([f for f in detections_data['frames'] if f['detection_count'] > 0])

        console.print(f"[green]✓ Total detections: {total_detections}[/green]")
        console.print(f"[green]✓ Frames with detections: {frames_with_detections}/{len(frame_files)}[/green]")

        class_counts = {}
        for frame in detections_data["frames"]:
            for det in frame["detections"]:
                class_name = det["class_name"]
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

        if class_counts:
            top_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            console.print(f"[cyan]Top 5 classes: {', '.join(f'{cls}:{cnt}' for cls, cnt in top_classes)}[/cyan]")

        self.__save_detections(episode_info, detections_data)

    def __save_detections(self, episode_info, detections_data: Dict[str, Any]) -> None:
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.object_detections)
        episode_dir.mkdir(parents=True, exist_ok=True)

        output_data = create_processing_metadata(
            episode_info=episode_info,
            processing_params={
                "model": self.model_name,
                "confidence_threshold": self.conf_threshold,
            },
            statistics={
                "total_frames": len(detections_data["frames"]),
                "total_detections": sum(f['detection_count'] for f in detections_data['frames']),
                "frames_with_detections": len([f for f in detections_data['frames'] if f['detection_count'] > 0]),
            },
            results_key="detections",
            results_data=detections_data["frames"],
        )

        detections_output = episode_dir / "detections.json"
        atomic_write_json(detections_output, output_data, indent=2, ensure_ascii=False)

        console.print(f"[green]✓ Saved object detections to: {detections_output}[/green]")

    @staticmethod
    def _cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class ObjectDetectionVisualizationSubProcessor(FrameSubProcessor):
    def __init__(self):
        super().__init__("Object Detection Visualization")
        self.logger = ErrorHandlingLogger("ObjectDetectionVisualizationSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def needs_ramdisk(self) -> bool:
        return False

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.object_visualizations)
        marker_file = episode_dir / ".visualization_complete"
        return [OutputSpec(path=marker_file, required=True)]

    def should_run(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> bool:
        episode_info = item.metadata["episode_info"]
        detection_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.object_detections)
        detection_file = detection_dir / "detections.json"

        if not detection_file.exists():
            console.print(f"[yellow]No object detections found for {episode_info.episode_code()}, skipping visualization[/yellow]")
            return False

        expected = self.get_expected_outputs(item)
        return any(str(exp.path) in str(miss.path) for exp in expected for miss in missing_outputs)

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:
        import cv2  # pylint: disable=import-outside-toplevel

        episode_info = item.metadata["episode_info"]
        detection_file = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.object_detections) / "detections.json"

        if not detection_file.exists():
            console.print(f"[yellow]No detections JSON found: {detection_file}[/yellow]")
            return

        if not ramdisk_frames_dir.exists():
            console.print(f"[yellow]No frames directory found: {ramdisk_frames_dir}[/yellow]")
            return

        with open(detection_file, 'r', encoding='utf-8') as f:
            detection_data = json.load(f)

        frames_with_detections = [f for f in detection_data.get("detections", []) if f['detection_count'] > 0]
        if not frames_with_detections:
            console.print(f"[yellow]No frames with detections for {episode_info.episode_code()}[/yellow]")
            return

        output_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.object_visualizations)
        output_dir.mkdir(parents=True, exist_ok=True)
        colors = self._generate_colors()
        conf_threshold = detection_data.get("processing_params", {}).get("confidence_threshold", 0.25)

        console.print(f"[cyan]Visualizing {len(frames_with_detections)} frames for {episode_info.episode_code()}[/cyan]")

        for frame_data in frames_with_detections:
            output_path = output_dir / frame_data['frame_name']
            if output_path.exists():
                continue

            frame_path = ramdisk_frames_dir / frame_data['frame_name']
            if not frame_path.exists():
                continue

            img = cv2.imread(str(frame_path))
            if img is None:
                continue

            self._draw_detections_on_frame(img, frame_data['detections'], colors, conf_threshold)
            cv2.imwrite(str(output_path), img)

        marker_file = output_dir / ".visualization_complete"
        marker_file.write_text(f"completed: {len(frames_with_detections)} frames")
        console.print(f"[green]✓ Visualized {len(frames_with_detections)} frames saved to: {output_dir}[/green]")

    @staticmethod
    def _draw_detections_on_frame(img, detections: List[Dict], colors: Dict[int, tuple], conf_threshold: float) -> None:
        import cv2  # pylint: disable=import-outside-toplevel

        for detection in detections:
            if detection['confidence'] < conf_threshold:
                continue

            class_id = detection['class_id']
            bbox = detection['bbox']
            x1, y1 = int(bbox['x1']), int(bbox['y1'])
            x2, y2 = int(bbox['x2']), int(bbox['y2'])
            color = colors.get(class_id, (0, 255, 0))

            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            label = f"{detection['class_name']} {detection['confidence']:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            label_y1 = max(y1 - 10, label_size[1])

            cv2.rectangle(img, (x1, label_y1 - label_size[1] - 5), (x1 + label_size[0], label_y1), color, -1)
            cv2.putText(img, label, (x1, label_y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    @staticmethod
    def _generate_colors(num_colors: int = 80) -> Dict[int, tuple]:
        np.random.seed(42)
        colors = {}
        for i in range(num_colors):
            colors[i] = tuple(int(x) for x in np.random.randint(50, 255, 3))
        return colors


class CharacterDetectionVisualizationSubProcessor(FrameSubProcessor):
    def __init__(self):
        super().__init__("Character Detection Visualization")
        self.logger = ErrorHandlingLogger("CharacterDetectionVisualizationSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def needs_ramdisk(self) -> bool:
        return False

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.character_visualizations)
        marker_file = episode_dir / ".visualization_complete"
        return [OutputSpec(path=marker_file, required=True)]

    def should_run(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> bool:
        episode_info = item.metadata["episode_info"]
        detection_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.character_detections)
        detection_file = detection_dir / "detections.json"

        if not detection_file.exists():
            console.print(f"[yellow]No character detections found for {episode_info.episode_code()}, skipping visualization[/yellow]")
            return False

        expected = self.get_expected_outputs(item)
        return any(str(exp.path) in str(miss.path) for exp in expected for miss in missing_outputs)

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:
        import cv2  # pylint: disable=import-outside-toplevel

        episode_info = item.metadata["episode_info"]
        detection_file = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.character_detections) / "detections.json"

        if not detection_file.exists():
            console.print(f"[yellow]No detections JSON found: {detection_file}[/yellow]")
            return

        if not ramdisk_frames_dir.exists():
            console.print(f"[yellow]No frames directory found: {ramdisk_frames_dir}[/yellow]")
            return

        with open(detection_file, 'r', encoding='utf-8') as f:
            detection_data = json.load(f)

        frames_with_detections = [f for f in detection_data.get("detections", []) if f.get('characters')]
        if not frames_with_detections:
            console.print(f"[yellow]No frames with character detections for {episode_info.episode_code()}[/yellow]")
            return

        output_dir = EpisodeManager.get_episode_subdir(episode_info, settings.output_subdirs.character_visualizations)
        output_dir.mkdir(parents=True, exist_ok=True)

        all_character_names = set()
        for frame_data in frames_with_detections:
            for char in frame_data.get('characters', []):
                all_character_names.add(char['name'])
        colors = self._generate_character_colors(all_character_names)

        console.print(f"[cyan]Visualizing {len(frames_with_detections)} frames with characters for {episode_info.episode_code()}[/cyan]")

        for frame_data in frames_with_detections:
            frame_name = frame_data.get('frame_file') or frame_data.get('frame')
            if not frame_name:
                continue

            output_path = output_dir / frame_name
            if output_path.exists():
                continue

            frame_path = ramdisk_frames_dir / frame_name
            if not frame_path.exists():
                continue

            img = cv2.imread(str(frame_path))
            if img is None:
                continue

            self._draw_characters_on_frame(img, frame_data['characters'], colors)
            cv2.imwrite(str(output_path), img)

        marker_file = output_dir / ".visualization_complete"
        marker_file.write_text(f"completed: {len(frames_with_detections)} frames")
        console.print(f"[green]✓ Visualized {len(frames_with_detections)} frames saved to: {output_dir}[/green]")

    @staticmethod
    def _draw_characters_on_frame(img, characters: List[Dict], colors: Dict[str, tuple]) -> None:
        import cv2  # pylint: disable=import-outside-toplevel

        for character in characters:
            name = character['name']
            confidence = character['confidence']
            bbox = character['bbox']

            x1, y1 = bbox['x1'], bbox['y1']
            x2, y2 = bbox['x2'], bbox['y2']
            color = colors.get(name, (0, 255, 0))

            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            label = f"{name} {confidence:.2f}"
            if "emotion" in character:
                emotion_label = character["emotion"]["label"]
                emotion_conf = character["emotion"]["confidence"]
                label += f" | {emotion_label} {emotion_conf:.2f}"

            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            label_y1 = max(y1 - 10, label_size[1])

            cv2.rectangle(img, (x1, label_y1 - label_size[1] - 5), (x1 + label_size[0], label_y1), color, -1)
            cv2.putText(img, label, (x1, label_y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    @staticmethod
    def _generate_character_colors(character_names: set) -> Dict[str, tuple]:
        np.random.seed(42)
        colors = {}
        sorted_names = sorted(character_names)
        for _, name in enumerate(sorted_names):
            colors[name] = tuple(int(x) for x in np.random.randint(50, 255, 3))
        return colors
