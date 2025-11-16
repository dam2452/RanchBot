import json
import logging
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
)

import cv2
import numpy as np
from rich.console import Console
from rich.progress import Progress
import torch
from transnetv2_pytorch import TransNetV2

from preprocessor.utils.error_handling_logger import ErrorHandlingLogger

console = Console()


class SceneDetector:
    DEFAULT_THRESHOLD = 0.5
    DEFAULT_MIN_SCENE_LEN = 10
    DEFAULT_OUTPUT_DIR = Path("scene_timestamps")

    def __init__(self, args: Dict):
        self.videos: Path = args["videos"]
        self.output_dir: Path = args.get("output_dir", self.DEFAULT_OUTPUT_DIR)
        self.threshold: float = args.get("threshold", self.DEFAULT_THRESHOLD)
        self.min_scene_len: int = args.get("min_scene_len", self.DEFAULT_MIN_SCENE_LEN)
        self.device: str = args.get("device", "cuda" if torch.cuda.is_available() else "cpu")

        self.logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=8,
        )

        self.model = None

    def work(self) -> int:
        try:
            self._exec()
        except Exception as e:
            self.logger.error(f"Scene detection failed: {e}")
        return self.logger.finalize()

    def _exec(self) -> None:
        console.print(f"[cyan]Scene detection using device: {self.device}[/cyan]")

        self._load_model()

        video_files = self._get_video_files()
        if not video_files:
            console.print("[yellow]No video files found[/yellow]")
            return

        console.print(f"[blue]Processing {len(video_files)} videos...[/blue]")

        with Progress() as progress:
            task = progress.add_task("[cyan]Detecting scenes...", total=len(video_files))

            for video_file in video_files:
                try:
                    self._process_video(video_file)
                except Exception as e:
                    self.logger.error(f"Failed to process {video_file}: {e}")
                finally:
                    progress.advance(task)

        console.print("[green]Scene detection completed[/green]")

    def _load_model(self) -> None:
        try:
            self.model = TransNetV2()
            if self.device == "cuda":
                self.model = self.model.cuda()

            console.print("[green]TransNetV2 model loaded[/green]")

        except ImportError:
            console.print("[yellow]TransNetV2 not installed. Using simplified detection.[/yellow]")
            self.model = None

    def _get_video_files(self) -> List[Path]:
        video_files = []

        if self.videos.is_file():
            return [self.videos]

        for ext in ("*.mp4", "*.avi", "*.mkv", "*.mov"):
            video_files.extend(self.videos.glob(f"**/{ext}"))

        return sorted(video_files)

    def _process_video(self, video_file: Path) -> None:
        console.print(f"[cyan]Processing: {video_file.name}[/cyan]")

        video_info = self._get_video_info(video_file)
        if not video_info:
            self.logger.error(f"Failed to get video info for {video_file}")
            return

        if self.model:
            scene_list = self._detect_scenes_transnetv2(video_file, video_info)
        else:
            scene_list = self._detect_scenes_simple(video_file, video_info)

        if not scene_list:
            console.print(f"[yellow]No scenes detected in {video_file.name}[/yellow]")
            return

        result = {
            "total_scenes": len(scene_list),
            "video_info": video_info,
            "detection_settings": {
                "threshold": self.threshold,
                "min_scene_len": self.min_scene_len,
                "method": "transnetv2" if self.model else "simple_histogram",
            },
            "scenes": scene_list,
        }

        output_file = self.output_dir / f"{video_file.stem}_scenes.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        console.print(f"[green]{video_file.name}: {len(scene_list)} scenes -> {output_file}[/green]")

    def _get_video_info(self, video_file: Path) -> Optional[Dict]:
        try:
            cap = cv2.VideoCapture(str(video_file))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            cap.release()

            return {
                "fps": fps,
                "duration": duration,
                "total_frames": total_frames,
            }
        except Exception as e:
            self.logger.error(f"Error reading video info: {e}")
            return None

    def _detect_scenes_transnetv2(self, video_file: Path, video_info: Dict) -> List[Dict]:
        try:
            _, single_frame_predictions, _ = self.model.predict_video(str(video_file))

            scene_changes = np.where(single_frame_predictions > self.threshold)[0]

            scenes = []
            fps = video_info["fps"]
            prev_frame = 0

            for frame_num in scene_changes:
                if frame_num - prev_frame < self.min_scene_len:
                    continue

                scene = {
                    "scene_number": len(scenes) + 1,
                    "start": {
                        "frame": int(prev_frame),
                        "seconds": float(prev_frame / fps),
                        "timecode": self._frame_to_timecode(prev_frame, fps),
                    },
                    "end": {
                        "frame": int(frame_num),
                        "seconds": float(frame_num / fps),
                        "timecode": self._frame_to_timecode(frame_num, fps),
                    },
                    "duration": float((frame_num - prev_frame) / fps),
                    "frame_count": int(frame_num - prev_frame),
                }
                scenes.append(scene)
                prev_frame = frame_num

            total_frames = video_info["total_frames"]
            if total_frames - prev_frame > self.min_scene_len:
                scene = {
                    "scene_number": len(scenes) + 1,
                    "start": {
                        "frame": int(prev_frame),
                        "seconds": float(prev_frame / fps),
                        "timecode": self._frame_to_timecode(prev_frame, fps),
                    },
                    "end": {
                        "frame": int(total_frames),
                        "seconds": float(total_frames / fps),
                        "timecode": self._frame_to_timecode(total_frames, fps),
                    },
                    "duration": float((total_frames - prev_frame) / fps),
                    "frame_count": int(total_frames - prev_frame),
                }
                scenes.append(scene)

            return scenes

        except Exception as e:
            self.logger.error(f"TransNetV2 detection failed: {e}")
            return []

    def _detect_scenes_simple(self, video_file: Path, video_info: Dict) -> List[Dict]:
        cap = cv2.VideoCapture(str(video_file))
        fps = video_info["fps"]
        total_frames = video_info["total_frames"]

        scenes = []
        prev_frame = None
        scene_changes = []

        frame_num = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_num % 5 != 0:
                frame_num += 1
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()

            if prev_frame is not None:
                diff = np.sum(np.abs(hist - prev_frame))
                if diff > self.threshold:
                    scene_changes.append(frame_num)

            prev_frame = hist
            frame_num += 1

        cap.release()

        prev_change = 0
        for change_frame in scene_changes:
            if change_frame - prev_change < self.min_scene_len:
                continue

            scene = {
                "scene_number": len(scenes) + 1,
                "start": {
                    "frame": int(prev_change),
                    "seconds": float(prev_change / fps),
                    "timecode": self._frame_to_timecode(prev_change, fps),
                },
                "end": {
                    "frame": int(change_frame),
                    "seconds": float(change_frame / fps),
                    "timecode": self._frame_to_timecode(change_frame, fps),
                },
                "duration": float((change_frame - prev_change) / fps),
                "frame_count": int(change_frame - prev_change),
            }
            scenes.append(scene)
            prev_change = change_frame

        if total_frames - prev_change > self.min_scene_len:
            scene = {
                "scene_number": len(scenes) + 1,
                "start": {
                    "frame": int(prev_change),
                    "seconds": float(prev_change / fps),
                    "timecode": self._frame_to_timecode(prev_change, fps),
                },
                "end": {
                    "frame": int(total_frames),
                    "seconds": float(total_frames / fps),
                    "timecode": self._frame_to_timecode(total_frames, fps),
                },
                "duration": float((total_frames - prev_change) / fps),
                "frame_count": int(total_frames - prev_change),
            }
            scenes.append(scene)

        return scenes

    @staticmethod
    def _frame_to_timecode(frame: int, fps: float) -> str:
        seconds = frame / fps
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * fps)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"
