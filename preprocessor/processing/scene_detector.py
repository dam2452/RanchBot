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

import decord
import numpy as np
from rich.progress import Progress
import torch
from transnetv2_pytorch import TransNetV2

from preprocessor.config.config import settings
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class SceneDetector:
    def __init__(self, args: Dict[str, Any]):
        self.videos: Path = args["videos"]
        self.output_dir: Path = args.get("output_dir", settings.scene_detection_output_dir)
        self.threshold: float = args.get("threshold", settings.scene_detection_threshold)
        self.min_scene_len: int = args.get("min_scene_len", settings.scene_detection_min_scene_len)

        self.logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=8,
        )

        self.model = None

    def work(self) -> int:
        try:
            self.__exec()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Scene detection failed: {e}")
        return self.logger.finalize()

    def __exec(self) -> None:
        console.print("[cyan]Scene detection using TransNetV2 on CUDA[/cyan]")

        self.__load_model()

        video_files = self.__get_video_files()
        if not video_files:
            console.print("[yellow]No video files found[/yellow]")
            return

        console.print(f"[blue]Processing {len(video_files)} videos...[/blue]")

        with Progress() as progress:
            task = progress.add_task("[cyan]Detecting scenes...", total=len(video_files))

            for video_file in video_files:
                try:
                    self.__process_video(video_file)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.error(f"Failed to process {video_file}: {e}")
                finally:
                    progress.advance(task)

        console.print("[green]Scene detection completed[/green]")

    def __load_model(self) -> None:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. TransNetV2 requires GPU.")

        console.print("[cyan]Loading TransNetV2 model on CUDA...[/cyan]")
        self.model = TransNetV2().cuda()
        console.print("[green]✓ TransNetV2 ready on CUDA[/green]")

    def __get_video_files(self) -> List[Path]:
        video_files = []

        if self.videos.is_file():
            return [self.videos]

        for ext in ("*.mp4", "*.avi", "*.mkv", "*.mov"):
            video_files.extend(self.videos.glob(f"**/{ext}"))

        return sorted(video_files)

    def __process_video(self, video_file: Path) -> None:
        output_file = self.output_dir / f"{video_file.stem}_scenes.json"

        if output_file.exists():
            console.print(f"[yellow]Skipping (already exists): {video_file.name}[/yellow]")
            return

        console.print(f"[cyan]Processing: {video_file.name}[/cyan]")

        video_info = self.__get_video_info(video_file)
        if not video_info:
            self.logger.error(f"Failed to get video info for {video_file}")
            return

        scene_list = self.__detect_scenes_transnetv2(video_file, video_info)

        if not scene_list:
            console.print(f"[yellow]No scenes detected in {video_file.name}[/yellow]")
            return

        result = {
            "total_scenes": len(scene_list),
            "video_info": video_info,
            "detection_settings": {
                "threshold": self.threshold,
                "min_scene_len": self.min_scene_len,
                "method": "transnetv2",
            },
            "scenes": scene_list,
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        console.print(f"[green]{video_file.name}: {len(scene_list)} scenes -> {output_file}[/green]")

    def __get_video_info(self, video_file: Path) -> Optional[Dict[str, Any]]:
        try:
            vr = decord.VideoReader(str(video_file), ctx=decord.gpu(0))
            fps = vr.get_avg_fps()
            total_frames = len(vr)
            duration = total_frames / fps if fps > 0 else 0

            return {
                "fps": fps,
                "duration": duration,
                "total_frames": total_frames,
            }
        except (RuntimeError, ValueError, OSError) as e:
            self.logger.error(f"Error reading video info: {e}")
            return None

    def __detect_scenes_transnetv2(  # pylint: disable=too-many-try-statements
        self, video_file: Path, video_info: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
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
                        "timecode": self.__frame_to_timecode(prev_frame, fps),
                    },
                    "end": {
                        "frame": int(frame_num),
                        "seconds": float(frame_num / fps),
                        "timecode": self.__frame_to_timecode(frame_num, fps),
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
                        "timecode": self.__frame_to_timecode(prev_frame, fps),
                    },
                    "end": {
                        "frame": int(total_frames),
                        "seconds": float(total_frames / fps),
                        "timecode": self.__frame_to_timecode(total_frames, fps),
                    },
                    "duration": float((total_frames - prev_frame) / fps),
                    "frame_count": int(total_frames - prev_frame),
                }
                scenes.append(scene)

            return scenes

        except (RuntimeError, ValueError, OSError) as e:
            self.logger.error(f"TransNetV2 detection failed: {e}")
            return []

    @staticmethod
    def __frame_to_timecode(frame: int, fps: float) -> str:
        seconds = frame / fps
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * fps)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"

    def cleanup(self) -> None:
        console.print("[cyan]Unloading TransNetV2 model and clearing GPU memory...[/cyan]")
        if hasattr(self, 'model') and self.model is not None:
            del self.model
            self.model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        console.print("[green]✓ TransNetV2 model unloaded, GPU memory cleared[/green]")
