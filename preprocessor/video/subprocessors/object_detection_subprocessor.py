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
from PIL import Image

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.path_manager import PathManager
from preprocessor.utils.batch_processor import BatchProcessor
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.utils.file_utils import atomic_write_json
from preprocessor.utils.metadata_utils import create_processing_metadata
from preprocessor.video.frame_processor import FrameSubProcessor


class ObjectDetectionSubProcessor(FrameSubProcessor):
    def __init__(self, model_name: str = "ustc-community/dfine-xlarge-obj2coco", conf_threshold: float = 0.25):
        super().__init__("Object Detection")
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.model: Optional[Any] = None
        self.image_processor: Optional[Any] = None
        self.logger = ErrorHandlingLogger("ObjectDetectionSubProcessor", logging.DEBUG, 15)
        self.batch_processor = BatchProcessor(8)

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
        self.__cleanup_memory()

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.object_detections)
        series_name = item.metadata["series_name"]
        path_manager = PathManager(series_name)
        detections_filename = path_manager.build_filename(
            episode_info,
            extension="json",
            suffix="_object_detections",
        )
        detections_output = episode_dir / detections_filename
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
            if f.is_file() and "frame_" in f.name
        ])

        if not frame_files:
            console.print(f"[yellow]No frames found in {ramdisk_frames_dir}[/yellow]")
            return

        console.print(f"[cyan]Detecting objects in {len(frame_files)} frames[/cyan]")

        def _process_batch(batch_paths: List[Path]) -> List[Dict[str, Any]]:
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

            batch_results = []
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
                batch_results.append(frame_result)

            for img in batch_images:
                img.close()
            return batch_results

        all_results = self.batch_processor.process(frame_files, _process_batch)

        detections_data = {
            "episode_code": episode_info.episode_code(),
            "model": self.model_name,
            "confidence_threshold": self.conf_threshold,
            "frames": all_results,
        }

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

        series_name = item.metadata["series_name"]
        self.__save_detections(episode_info, detections_data, series_name)

    def __save_detections(self, episode_info, detections_data: Dict[str, Any], series_name: str) -> None:
        episode_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.object_detections)
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
        path_manager = PathManager(series_name)
        detections_filename = path_manager.build_filename(
            episode_info,
            extension="json",
            suffix="_object_detections",
        )
        detections_output = episode_dir / detections_filename
        atomic_write_json(detections_output, output_data, indent=2, ensure_ascii=False)

        console.print(f"[green]✓ Saved object detections to: {detections_output}[/green]")

    @staticmethod
    def __cleanup_memory() -> None:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()