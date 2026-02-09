import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Tuple,
)

import cv2
import numpy as np

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.path_manager import PathManager
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger
from preprocessor.video.frame_processor import FrameSubProcessor


class ObjectDetectionVisualizationSubProcessor(FrameSubProcessor):
    def __init__(self):
        super().__init__("Object Detection Visualization")
        self.logger = ErrorHandlingLogger("ObjectDetectionVisualizationSubProcessor", logging.DEBUG, 15)

    def initialize(self) -> None:
        pass

    def cleanup(self) -> None:
        pass

    def needs_ramdisk(self) -> bool:
        return False

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        episode_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.object_visualizations)
        marker_file = episode_dir / ".visualization_complete"
        return [OutputSpec(path=marker_file, required=True)]

    def should_run(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> bool:
        episode_info = item.metadata["episode_info"]
        detection_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.object_detections)
        detection_files = list(detection_dir.glob("*_object_detections.json"))
        detection_file = detection_files[0] if detection_files else None

        if not detection_file or not detection_file.exists():
            console.print(f"[yellow]No object detections found for {episode_info.episode_code()}, skipping visualization[/yellow]")
            return False

        expected = self.get_expected_outputs(item)
        return any(str(exp.path) in str(miss.path) for exp in expected for miss in missing_outputs)

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:
        episode_info = item.metadata["episode_info"]
        detection_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.object_detections)

        detection_data = self._load_detection_file(
            detection_dir,
            ramdisk_frames_dir,
            "*_object_detections.json",
        )
        if detection_data is None:
            return

        frames_with_detections = [f for f in detection_data.get("detections", []) if f['detection_count'] > 0]
        if not frames_with_detections:
            console.print(f"[yellow]No frames with detections for {episode_info.episode_code()}[/yellow]")
            return

        output_dir = PathManager(episode_info.series_name or "unknown").get_episode_dir(episode_info,settings.output_subdirs.object_visualizations)
        output_dir.mkdir(parents=True, exist_ok=True)
        colors = self.__generate_colors()
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

            self.__draw_detections_on_frame(img, frame_data['detections'], colors, conf_threshold)
            cv2.imwrite(str(output_path), img)

        marker_file = output_dir / ".visualization_complete"
        marker_file.write_text(f"completed: {len(frames_with_detections)} frames")
        console.print(f"[green]✓ Visualized {len(frames_with_detections)} frames saved to: {output_dir}[/green]")

    @staticmethod
    def __draw_detections_on_frame(img, detections: List[Dict[str, Any]], colors: Dict[int, Tuple[int, int, int]], conf_threshold: float) -> None:
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
            FrameSubProcessor._draw_label_on_bbox(img, label, x1, y1, color)

    @staticmethod
    def __generate_colors(num_colors: int = 80) -> Dict[int, Tuple[int, int, int]]:
        np.random.seed(42)
        colors = {}
        for i in range(num_colors):
            colors[i] = tuple(int(x) for x in np.random.randint(50, 255, 3))
        return colors
