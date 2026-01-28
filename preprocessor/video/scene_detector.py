import gc
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
import torch
from transnetv2_pytorch import TransNetV2

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.core.output_path_builder import OutputPathBuilder
from preprocessor.utils.console import console
from preprocessor.utils.file_utils import atomic_write_json


class SceneDetector(BaseProcessor):
    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=8,
            loglevel=logging.DEBUG,
        )

        self.videos: Path = self._args["videos"]
        self.output_dir: Path = self._args.get("output_dir", settings.scene_detection.output_dir)
        self.threshold: float = self._args.get("threshold", settings.scene_detection.threshold)
        self.min_scene_len: int = self._args.get("min_scene_len", settings.scene_detection.min_scene_len)

        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

        self.model = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "videos" not in args:
            raise ValueError("videos path is required")
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. TransNetV2 requires GPU.")

    def cleanup(self) -> None:
        console.print("[cyan]Unloading TransNetV2 model and clearing GPU memory...[/cyan]")
        if hasattr(self, 'model') and self.model is not None:
            del self.model
            self.model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        console.print("[green]✓ TransNetV2 model unloaded, GPU memory cleared[/green]")

    def _get_processing_items(self) -> List[ProcessingItem]:
        return self._create_video_processing_items(
            source_path=self.videos,
            extensions=self.get_video_glob_patterns(),
            episode_manager=self.episode_manager,
            skip_unparseable=False,
        )

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata.get("episode_info")

        if episode_info:
            output_filename = self.episode_manager.file_naming.build_filename(
                episode_info,
                extension="json",
                suffix="scenes",
            )
            output_path = OutputPathBuilder.build_scene_path(episode_info, output_filename)
        else:
            output_filename = f"{item.input_path.stem}_scenes.json"
            output_path = OutputPathBuilder.get_episode_dir(None, settings.output_subdirs.scenes) / output_filename

        return [OutputSpec(path=output_path, required=True)]

    def _get_processing_info(self) -> List[str]:
        return ["[cyan]Scene detection using TransNetV2 on CUDA[/cyan]"]

    def _load_resources(self) -> bool:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. TransNetV2 requires GPU.")

        console.print("[cyan]Loading TransNetV2 model on CUDA...[/cyan]")
        self.model = TransNetV2().cuda()
        console.print("[green]✓ TransNetV2 ready on CUDA[/green]")
        return True

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        video_file = item.input_path
        output_file = missing_outputs[0].path

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

        atomic_write_json(output_file, result, indent=2, ensure_ascii=False)

        console.print(f"[green]{video_file.name}: {len(scene_list)} scenes -> {output_file}[/green]")

    def __detect_scenes_transnetv2(
        self, video_file: Path, video_info: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        try:  # pylint: disable=too-many-try-statements
            _, single_frame_predictions, _ = self.model.predict_video(str(video_file))

            scene_changes = np.where(single_frame_predictions > self.threshold)[0]

            scenes = []
            fps = video_info["fps"]
            prev_frame = 0

            for frame_num in scene_changes:
                if frame_num - prev_frame < self.min_scene_len:
                    continue

                scene = self.__create_scene_dict(len(scenes) + 1, prev_frame, frame_num, fps)
                scenes.append(scene)
                prev_frame = frame_num

            total_frames = video_info["total_frames"]
            if total_frames - prev_frame > self.min_scene_len:
                scene = self.__create_scene_dict(len(scenes) + 1, prev_frame, total_frames, fps)
                scenes.append(scene)

            return scenes

        except (RuntimeError, ValueError, OSError) as e:
            self.logger.error(f"TransNetV2 detection failed: {e}")
            return []

    def __get_video_info(self, video_file: Path) -> Optional[Dict[str, Any]]:
        try:
            vr = decord.VideoReader(str(video_file), ctx=decord.cpu(0))
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

    def __create_scene_dict(self, scene_number: int, start_frame: int, end_frame: int, fps: float) -> Dict[str, Any]:
        return {
            "scene_number": scene_number,
            "start": {
                "frame": int(start_frame),
                "seconds": float(start_frame / fps),
                "timecode": self.__frame_to_timecode(start_frame, fps),
            },
            "end": {
                "frame": int(end_frame),
                "seconds": float(end_frame / fps),
                "timecode": self.__frame_to_timecode(end_frame, fps),
            },
            "duration": float((end_frame - start_frame) / fps),
            "frame_count": int(end_frame - start_frame),
        }

    @staticmethod
    def __frame_to_timecode(frame: int, fps: float) -> str:
        seconds = frame / fps
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * fps)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"
