from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
    as_completed,
)
import json
import logging
from pathlib import Path
import re
import subprocess
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from rich.console import Console
from rich.progress import Progress

from bot.utils.resolution import Resolution
from preprocessor.core.state_manager import StateManager
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger

console = Console()


class VideoTranscoder:
    DEFAULT_OUTPUT_DIR: Path = Path("transcoded_videos")
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

        self.__episodes_info: Optional[Dict[str, Any]] = None
        episodes_json_path = args.get("episodes_info_json")
        if episodes_json_path:
            with open(episodes_json_path, "r", encoding="utf-8") as f:
                self.__episodes_info = json.load(f)

        self.__state_manager: Optional[StateManager] = args.get("state_manager")
        self.__series_name: str = args.get("series_name", "unknown")

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
                episode_id = self.__get_episode_id(video_file)

                if self.__state_manager and self.__state_manager.is_step_completed("transcode", episode_id):
                    console.print(f"[yellow]Skipping (already done): {episode_id}[/yellow]")
                    progress.advance(task)
                    continue

                if self.__state_manager:
                    self.__state_manager.mark_step_started("transcode", episode_id)

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
                    episode_id = self.__get_episode_id(video_file)

                    if self.__state_manager and self.__state_manager.is_step_completed("transcode", episode_id):
                        console.print(f"[yellow]Skipping (already done): {episode_id}[/yellow]")
                        progress.advance(task)
                        continue

                    if self.__state_manager:
                        self.__state_manager.mark_step_started("transcode", episode_id)

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

    @staticmethod
    def __get_episode_id(video_file: Path) -> str:
        match = re.search(r"E(\d+)", video_file.stem, re.IGNORECASE)
        if match:
            return f"E{match.group(1)}"
        return video_file.stem

    def __process_single_video(self, video_file: Path) -> None:
        match = re.search(r"E(\d+)", video_file.stem, re.IGNORECASE)
        if not match:
            self.__logger.error(f"Cannot extract episode number from {video_file.name}")
            return

        absolute_episode = int(match.group(1))
        season_number, relative_episode = self.__find_episode_info(absolute_episode)

        if season_number is None:
            self.__logger.error(f"Episode {absolute_episode} not found in episodes_info.json")
            return

        output_path = self.__build_output_path(self.__series_name, season_number, relative_episode)

        try:
            self.__transcode_video(video_file, output_path)
            self.__logger.info(f"Processed: {video_file} -> {output_path}")
        except subprocess.CalledProcessError as e:
            self.__logger.error(f"FFmpeg failed for {video_file}: {e}")

    # noinspection PyShadowingNames
    def __find_episode_info(self, absolute_episode: int) -> Tuple[Optional[int], Optional[int]]:
        season_number: int = 1
        relative_episode: int = absolute_episode

        if not self.__episodes_info:
            return season_number, relative_episode

        for season in self.__episodes_info.get("seasons", []):
            season_num: int = season.get("season_number", 1)
            episodes: List[Dict[str, Any]] = sorted(
                season.get("episodes", []),
                key=lambda ep: ep["episode_number"],
            )

            for idx, ep in enumerate(episodes):
                if ep["episode_number"] == absolute_episode:
                    return season_num, idx + 1

        return None, None

    def __build_output_path(self, series_name: str, season_number: int, relative_episode: int) -> Path:
        transcoded_name = f"{series_name}_S{season_number:02d}E{relative_episode:02d}.mp4"
        if season_number == 0:
            output_dir = self.__output_videos / "Specjalne"
        else:
            output_dir = self.__output_videos / f"Sezon {season_number}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / transcoded_name

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
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

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
