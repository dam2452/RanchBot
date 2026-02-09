import json
import logging
from pathlib import Path
import shutil
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import cv2

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.episodes import EpisodeManager
from preprocessor.utils.console import console

# pylint: disable=duplicate-code


class FrameProcessor(BaseProcessor):
    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=15,
            loglevel=logging.DEBUG,
        )

        self.frames_dir: Path = Path(
            self._args.get("frames_dir", settings.frame_export.get_output_dir(self.series_name)),
        )
        self.ramdisk_path: Path = Path(self._args.get("ramdisk_path", "/dev/shm"))

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

        self.sub_processors: List['FrameSubProcessor'] = []

    def _validate_args(self, args: Dict[str, Any]) -> None:
        pass

    def get_output_subdir(self) -> str:
        return settings.output_subdirs.frames

    def add_sub_processor(self, processor: 'FrameSubProcessor') -> None:
        self.sub_processors.append(processor)

    def _get_processing_items(self) -> List[ProcessingItem]:
        return self._get_episode_processing_items_from_metadata(
            "**/*_frame_metadata.json",
            self.frames_dir,
            self.episode_manager,
        )

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        outputs = []
        for sub_processor in self.sub_processors:
            outputs.extend(sub_processor.get_expected_outputs(item))
        return outputs

    def cleanup(self) -> None:
        for sub_processor in self.sub_processors:
            sub_processor.finalize()
        console.print("[green]✓ All sub-processors finalized[/green]")

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        metadata_file = item.input_path
        episode_info = item.metadata["episode_info"]

        frames_episode_dir = metadata_file.parent
        season = episode_info.season
        episode = episode_info.relative_episode

        any_sub_processor_will_run = any(
            sub_processor.should_run(item, missing_outputs)
            for sub_processor in self.sub_processors
        )

        if not any_sub_processor_will_run:
            for sub_processor in self.sub_processors:
                console.print(f"[yellow]Skipping: {sub_processor.name} (output exists)[/yellow]")
            return

        any_sub_processor_needs_ramdisk = any(
            sub_processor.should_run(item, missing_outputs) and sub_processor.needs_ramdisk()
            for sub_processor in self.sub_processors
        )

        if any_sub_processor_needs_ramdisk:
            ramdisk_episode_dir = self.ramdisk_path / "frames" / f"S{season:02d}" / f"E{episode:02d}"
            try:
                self.__copy_frames_to_ramdisk(frames_episode_dir, ramdisk_episode_dir)

                for sub_processor in self.sub_processors:
                    if sub_processor.should_run(item, missing_outputs):
                        console.print(f"[cyan]Running: {sub_processor.name}[/cyan]")
                        sub_processor.process(item, ramdisk_episode_dir)
                    else:
                        console.print(f"[yellow]Skipping: {sub_processor.name} (output exists)[/yellow]")

            finally:
                self.__cleanup_ramdisk(ramdisk_episode_dir)
        else:
            for sub_processor in self.sub_processors:
                if sub_processor.should_run(item, missing_outputs):
                    console.print(f"[cyan]Running: {sub_processor.name}[/cyan]")
                    sub_processor.process(item, frames_episode_dir)
                else:
                    console.print(f"[yellow]Skipping: {sub_processor.name} (output exists)[/yellow]")

    @staticmethod
    def __copy_frames_to_ramdisk(source_dir: Path, dest_dir: Path) -> None:
        dest_dir.mkdir(parents=True, exist_ok=True)

        frame_files = list(source_dir.glob("*frame_*.jpg"))
        console.print(f"[cyan]Copying {len(frame_files)} frames to RAMdisk: {dest_dir}[/cyan]")

        for frame_file in frame_files:
            shutil.copy2(frame_file, dest_dir / frame_file.name)

        console.print("[green]✓ Frames copied to RAMdisk[/green]")

    @staticmethod
    def __cleanup_ramdisk(ramdisk_dir: Path) -> None:
        if ramdisk_dir.exists():
            shutil.rmtree(ramdisk_dir)
            console.print(f"[green]✓ RAMdisk cleaned: {ramdisk_dir}[/green]")


class FrameSubProcessor:
    def __init__(self, name: str):
        self.name = name

    def get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        raise NotImplementedError

    def should_run(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> bool:
        expected = self.get_expected_outputs(item)
        return any(str(exp.path) in str(miss.path) for exp in expected for miss in missing_outputs)

    def needs_ramdisk(self) -> bool:
        return True

    def process(self, item: ProcessingItem, ramdisk_frames_dir: Path) -> None:
        raise NotImplementedError

    @staticmethod
    def _load_frame_files_from_ramdisk(ramdisk_frames_dir: Path) -> List[Path]:
        return sorted([
            f for f in ramdisk_frames_dir.glob("*.jpg")
            if f.is_file() and "frame_" in f.name
        ])

    def _load_frames_with_warning(self, ramdisk_frames_dir: Path) -> Optional[List[Path]]:
        frame_files = self._load_frame_files_from_ramdisk(ramdisk_frames_dir)
        if not frame_files:
            console.print(f"[yellow]No frames found in {ramdisk_frames_dir}[/yellow]")
            return None
        return frame_files

    @staticmethod
    def _load_detection_file(
        detection_dir: Path,
        ramdisk_frames_dir: Path,
        glob_pattern: str,
    ) -> Optional[Dict[str, Any]]:
        detection_files = list(detection_dir.glob(glob_pattern))
        detection_file = detection_files[0] if detection_files else None

        if not detection_file or not detection_file.exists():
            console.print(f"[yellow]No detections JSON found in {detection_dir}[/yellow]")
            return None

        if not ramdisk_frames_dir.exists():
            console.print(f"[yellow]No frames directory found: {ramdisk_frames_dir}[/yellow]")
            return None

        with open(detection_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _load_frame_requests_from_metadata(metadata_file: Path) -> Optional[List[Dict[str, Any]]]:
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        frame_requests = metadata.get("frames", [])
        if not frame_requests:
            console.print(f"[yellow]No frames in metadata for {metadata_file}[/yellow]")
            return None

        return frame_requests

    @staticmethod
    def _draw_label_on_bbox(
        img,
        label: str,
        x1: int,
        y1: int,
        color: Tuple[int, int, int],
    ) -> None:
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_y1 = max(y1 - 10, label_size[1])

        cv2.rectangle(img, (x1, label_y1 - label_size[1] - 5), (x1 + label_size[0], label_y1), color, -1)
        cv2.putText(img, label, (x1, label_y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    def finalize(self) -> None:
        if hasattr(self, 'logger'):
            self.logger.finalize()
