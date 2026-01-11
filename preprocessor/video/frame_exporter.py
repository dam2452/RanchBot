from datetime import datetime
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from PIL import Image
import decord

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.enums import KeyframeStrategy
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.embeddings.strategies.strategy_factory import KeyframeStrategyFactory
from preprocessor.utils.console import console
from preprocessor.video.base_video_processor import BaseVideoProcessor


class FrameExporter(BaseVideoProcessor):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=10,
            input_videos_key="transcoded_videos",
        )
        decord.bridge.set_bridge('native')

        self.output_frames: Path = Path(self._args.get("output_frames", settings.frame_export.output_dir))
        self.output_frames.mkdir(parents=True, exist_ok=True)

        self.scene_timestamps_dir: Path = Path(self._args.get("scene_timestamps_dir", settings.scene_detection.output_dir))
        self.resize_height: int = self._args.get("frame_height", settings.frame_export.frame_height)

        keyframe_strategy_str = self._args.get("keyframe_strategy", settings.embedding.keyframe_strategy)
        self.keyframe_strategy = KeyframeStrategy(keyframe_strategy_str)
        self.keyframe_interval: int = self._args.get("keyframe_interval", settings.embedding.keyframe_interval)
        self.frames_per_scene: int = self._args.get("frames_per_scene", settings.embedding.frames_per_scene)

        self.strategy = KeyframeStrategyFactory.create(
            self.keyframe_strategy,
            self.keyframe_interval,
            self.frames_per_scene,
        )

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "transcoded_videos" not in args:
            raise ValueError("transcoded_videos path is required")

        videos_path = Path(args["transcoded_videos"])
        if not videos_path.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{videos_path}'")

        if "scene_timestamps_dir" in args:
            scene_path = Path(args["scene_timestamps_dir"])
            if not scene_path.exists():
                console.print(f"[yellow]Warning: Scene timestamps directory does not exist: {scene_path}[/yellow]")

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        season = episode_info.season
        episode = episode_info.relative_episode
        episode_dir = self.output_frames / f"S{season:02d}" / f"E{episode:02d}"

        metadata_file = episode_dir / "frame_metadata.json"
        return [OutputSpec(path=metadata_file, required=True)]

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        episode_info = item.metadata["episode_info"]
        episode_dir = self.__get_episode_dir(episode_info)
        episode_dir.mkdir(parents=True, exist_ok=True)

        data = self.__prepare_data(episode_info)
        frame_requests = self.strategy.extract_frame_requests(item.input_path, data)

        if not frame_requests:
            console.print(f"[yellow]No frames to extract for {item.input_path.name}[/yellow]")
            return

        console.print(f"[cyan]Extracting {len(frame_requests)} keyframes from {item.input_path.name}[/cyan]")

        try:
            self.__extract_frames(item.input_path, frame_requests, episode_dir)
        except Exception as e:
            self.logger.error(f"Failed to extract frames from {item.input_path}: {e}")
            raise

        self.__write_metadata(episode_dir, frame_requests, episode_info, item.input_path)
        console.print(f"[green]✓ Exported {len(frame_requests)} frames to {episode_dir}[/green]")

    def __get_episode_dir(self, episode_info) -> Path:
        season = episode_info.season
        episode = episode_info.relative_episode
        return self.output_frames / f"S{season:02d}" / f"E{episode:02d}"

    def __prepare_data(self, episode_info) -> Dict[str, Any]:
        data = {}
        scene_timestamps = self.__load_scene_timestamps(episode_info)
        if scene_timestamps:
            data["scene_timestamps"] = scene_timestamps
        return data

    def __extract_frames(self, video_file: Path, frame_requests: List[Dict[str, Any]], episode_dir: Path) -> None:
        vr = decord.VideoReader(str(video_file), ctx=decord.cpu(0))
        frame_numbers = [req["frame_number"] for req in frame_requests]

        with self.progress.track_operation(f"Keyframes ({len(frame_numbers)} frames)", len(frame_numbers)) as tracker:
            for idx, frame_num in enumerate(frame_numbers, 1):
                self.__extract_and_save_frame(vr, frame_num, episode_dir)
                tracker.update(idx, interval=50)

        del vr

    def __extract_and_save_frame(self, vr, frame_num: int, episode_dir: Path) -> None:
        frame_np = vr[frame_num].asnumpy()
        frame_pil = Image.fromarray(frame_np)

        resized = self.__resize_frame(frame_pil)
        filename = f"frame_{frame_num:06d}.jpg"
        resized.save(episode_dir / filename, quality=90)

    def __resize_frame(self, frame: Image.Image) -> Image.Image:
        aspect_ratio = frame.width / frame.height
        new_width = int(self.resize_height * aspect_ratio)
        return frame.resize((new_width, self.resize_height), Image.Resampling.LANCZOS)

    @staticmethod
    def __calculate_total_scenes(frame_requests: List[Dict[str, Any]]) -> int:
        scene_numbers = set(f.get("scene_number", -1) for f in frame_requests)
        has_invalid = -1 in scene_numbers
        return len(scene_numbers) - (1 if has_invalid else 0)

    def __write_metadata(self, episode_dir: Path, frame_requests: List[Dict[str, Any]], episode_info, source_video: Path) -> None:
        frame_types_count = {}
        frames_with_paths = []

        for frame in frame_requests:
            frame_type = frame.get("type", "unknown")
            frame_types_count[frame_type] = frame_types_count.get(frame_type, 0) + 1

            frame_with_path = frame.copy()
            frame_num = frame["frame_number"]
            frame_with_path["frame_path"] = f"frame_{frame_num:06d}.jpg"
            frames_with_paths.append(frame_with_path)

        metadata = {
            "generated_at": datetime.now().isoformat(),
            "episode_info": {
                "season": episode_info.season,
                "episode_number": episode_info.relative_episode,
                "absolute_episode": episode_info.absolute_episode,
            },
            "source_video": str(source_video),
            "processing_parameters": {
                "frame_height": self.resize_height,
                "keyframe_strategy": self.keyframe_strategy.value,
                "keyframe_interval": self.keyframe_interval,
                "frames_per_scene": self.frames_per_scene,
            },
            "statistics": {
                "total_frames": len(frame_requests),
                "frame_types": frame_types_count,
                "total_scenes": self.__calculate_total_scenes(frame_requests),
                "timestamp_range": {
                    "start": min((f.get("timestamp", 0) for f in frame_requests), default=0),
                    "end": max((f.get("timestamp", 0) for f in frame_requests), default=0),
                },
            },
            "frames": frames_with_paths,
        }
        metadata_file = episode_dir / "frame_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def __load_scene_timestamps(self, episode_info) -> Optional[Dict[str, Any]]:
        if not self.scene_timestamps_dir or not self.scene_timestamps_dir.exists():
            return None
        return EpisodeManager.load_scene_timestamps(episode_info, self.scene_timestamps_dir, self.logger)
