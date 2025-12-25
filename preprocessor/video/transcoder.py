from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
    as_completed,
)
import json
import logging
import os
from pathlib import Path
import subprocess
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from rich.progress import Progress

from bot.utils.resolution import Resolution
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.core.state_manager import StateManager
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class VideoTranscoder:
    DEFAULT_OUTPUT_DIR: Path = Path("/app/output_data/transcoded_videos")
    DEFAULT_RESOLUTION: Resolution = Resolution.R1080P
    DEFAULT_CODEC: str = "h264_nvenc"
    DEFAULT_PRESET: str = "slow"
    DEFAULT_CRF: int = 31
    DEFAULT_GOP_SIZE: float = 0.5
    DEFAULT_MAX_WORKERS: int = 1

    def __init__(self, args: Dict[str, Any]) -> None:
        self.__resolution: Resolution = args["resolution"]

        self.__input_videos: Path = Path(args["videos"])
        if not self.__input_videos.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{self.__input_videos}'")

        self.__output_videos: Path = Path(args["transcoded_videos"])
        self.__output_videos.mkdir(parents=True, exist_ok=True)

        self.__codec: str = str(args["codec"])
        self.__preset: str = str(args["preset"])
        self.__crf: int = int(args["crf"])
        self.__gop_size: float = float(args["gop_size"])
        self.__max_workers: int = int(args.get("max_workers", self.DEFAULT_MAX_WORKERS))

        self.__logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=3,
        )

        self.__state_manager: Optional[StateManager] = args.get("state_manager")
        self.__series_name: str = args.get("series_name", "unknown")

        episodes_json_path = args.get("episodes_info_json")
        self.__episode_manager = EpisodeManager(episodes_json_path, self.__series_name)

    def work(self) -> int:
        video_files: List[Path] = sorted(self.__input_videos.rglob("*.mp4"))

        if not video_files:
            self.__logger.warning("No video files found")
            return self.__logger.finalize()

        console.print(f"[blue]Found {len(video_files)} video files to transcode[/blue]")
        console.print(f"[cyan]Using {self.__max_workers} worker(s)[/cyan]")

        if self.__state_manager:
            progress = self.__state_manager.create_progress_bar(
                len(video_files),
                "Transcoding videos",
            )
        else:
            progress = Progress()

        if self.__max_workers == 1:
            return self.__work_sequential(video_files, progress)
        return self.__work_parallel(video_files, progress)

    def __work_sequential(self, video_files: List[Path], progress: Progress) -> int:
        with progress:
            task = progress.add_task("[cyan]Transcoding...", total=len(video_files))

            for video_file in video_files:
                episode_id = self.__prepare_video_for_processing(video_file, progress, task)
                if episode_id is None:
                    continue

                self.__process_single_video(video_file)

                if self.__state_manager:
                    self.__state_manager.mark_step_completed("transcode", episode_id)

                progress.advance(task)

        return self.__logger.finalize()

    def __work_parallel(self, video_files: List[Path], progress: Progress) -> int:
        with progress:
            task = progress.add_task("[cyan]Transcoding...", total=len(video_files))

            with ThreadPoolExecutor(max_workers=self.__max_workers) as executor:
                futures: Dict[Future, Tuple[Path, str]] = {}
                for video_file in video_files:
                    episode_id = self.__prepare_video_for_processing(video_file, progress, task)
                    if episode_id is None:
                        continue

                    future = executor.submit(self.__process_single_video, video_file)
                    futures[future] = (video_file, episode_id)

                for future in as_completed(futures):
                    video_file, episode_id = futures[future]
                    try:
                        future.result()
                        if self.__state_manager:
                            self.__state_manager.mark_step_completed("transcode", episode_id)
                    except (subprocess.CalledProcessError, OSError, ValueError) as e:
                        self.__logger.error(f"Failed to process {video_file}: {e}")
                    finally:
                        progress.advance(task)

        return self.__logger.finalize()

    def __prepare_video_for_processing(self, video_file: Path, progress, task) -> Optional[str]:
        episode_info = self.__episode_manager.parse_filename(video_file)
        if not episode_info:
            self.__logger.error(f"Cannot parse episode info from {video_file.name}")
            progress.advance(task)
            return None

        episode_id = EpisodeManager.get_episode_id_for_state(episode_info)
        output_path = self.__episode_manager.build_output_path(episode_info, self.__output_videos, ".mp4")

        should_skip, skip_message = self.__should_skip_video(episode_id, output_path)
        if should_skip:
            console.print(skip_message)
            progress.advance(task)
            return None

        if self.__state_manager:
            self.__state_manager.mark_step_started("transcode", episode_id)

        return episode_id

    def __should_skip_video(self, episode_id: str, output_path: Optional[Path]) -> Tuple[bool, str]: #Parameter 'video_file' value is not used
        if output_path and output_path.exists() and output_path.stat().st_size > 0:
            return True, f"[yellow]Skipping (already exists): {episode_id}[/yellow]"

        if self.__state_manager and self.__state_manager.is_step_completed("transcode", episode_id):
            return True, f"[yellow]Skipping (marked as done): {episode_id}[/yellow]"

        return False, ""

    def __process_single_video(self, video_file: Path) -> None:
        episode_info = self.__episode_manager.parse_filename(video_file)
        if not episode_info:
            self.__logger.error(f"Cannot extract episode info from {video_file.name}")
            return

        output_path = self.__episode_manager.build_output_path(episode_info, self.__output_videos, ".mp4")

        try:
            self.__transcode_video(video_file, output_path)
            self.__logger.info(f"Processed: {video_file} -> {output_path}")
        except subprocess.CalledProcessError as e:
            self.__logger.error(f"FFmpeg failed for {video_file}: {e}")

    def __transcode_video(self, input_video: Path, output_video: Path) -> None:
        fps = self.__get_framerate(input_video)

        vf_filter = (
            f"scale={self.__resolution.width}:{self.__resolution.height}:force_original_aspect_ratio=decrease,"
            f"pad={self.__resolution.width}:{self.__resolution.height}:(ow-iw)/2:(oh-ih)/2:black"
        )

        command = [
            "ffmpeg",
            "-v", "error",
            "-stats",
            "-hide_banner",
            "-y",
            "-i", str(input_video),
            "-c:v", self.__codec,
            "-preset", self.__preset,
            "-profile:v", "main",
            "-cq:v", str(self.__crf),
            "-g", str(int(fps * self.__gop_size)),
            "-c:a", "aac",
            "-b:a", "128k",
            "-ac", "2",
            "-vf", vf_filter,
            "-movflags", "+faststart",
            str(output_video),
        ]

        self.__logger.debug(f"Transcoding: {input_video.name} -> {output_video.name}")
        self.__logger.debug(f"FFmpeg command: {' '.join(command)}")
        self.__logger.debug(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'not set')[:200]}")

        try:
            subprocess.run(command, check=True, capture_output=False, text=True)
        except subprocess.CalledProcessError as e:
            self.__logger.error(f"FFmpeg failed with exit code: {e.returncode}")
            raise

    @staticmethod
    def __get_framerate(video: Path) -> float:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "json",
            str(video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data: Dict[str, Any] = json.loads(result.stdout)
        streams: List[Dict[str, Any]] = probe_data.get("streams", [])
        if not streams:
            raise ValueError(f"No video streams found in {video}")
        r_frame_rate: Optional[str] = streams[0].get("r_frame_rate")
        if not r_frame_rate:
            raise ValueError(f"Frame rate not found in {video}")
        num, denom = [int(x) for x in r_frame_rate.split("/")]

        return num / denom
