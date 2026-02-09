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
)

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.constants import DEFAULT_VIDEO_EXTENSION
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.core.processor_registry import register_processor
from preprocessor.utils.constants import (
    FfprobeKeys,
    FfprobeStreamKeys,
)
from preprocessor.utils.resolution import Resolution


@register_processor("transcode")
class VideoTranscoder(BaseProcessor):
    REQUIRES = ["videos"]
    PRODUCES = ["transcoded_videos"]
    PRIORITY = 10
    DESCRIPTION = "Transcode videos to H.264 with consistent format"

    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=3,
            loglevel=logging.DEBUG,
        )

        self.input_videos: Path = Path(self._args["videos"])
        self.subdirectory_filter: Optional[str] = None
        episodes_json_path = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_json_path, self.series_name)

        self.resolution: Resolution = self._args["resolution"]
        self.codec: str = str(self._args["codec"])
        self.preset: str = "p7"
        self.video_bitrate_mbps: Optional[float] = self._args.get("video_bitrate_mbps")
        self.minrate_mbps: Optional[float] = self._args.get("minrate_mbps")
        self.maxrate_mbps: Optional[float] = self._args.get("maxrate_mbps")
        self.bufsize_mbps: Optional[float] = self._args.get("bufsize_mbps")
        self.audio_bitrate_kbps: int = int(self._args.get("audio_bitrate_kbps", 128))
        self.gop_size: float = float(self._args["gop_size"])

    def _get_processing_items(self) -> List[ProcessingItem]:
        return self._create_video_processing_items(
            source_path=self.input_videos,
            extensions=self.get_video_glob_patterns(),
            episode_manager=self.episode_manager,
            skip_unparseable=True,
            subdirectory_filter=self.subdirectory_filter,
        )

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "videos" not in args:
            raise ValueError("videos path is required")
        if "resolution" not in args:
            raise ValueError("resolution is required")
        if "codec" not in args:
            raise ValueError("codec is required")
        if "gop_size" not in args:
            raise ValueError("gop_size is required")
        if "transcoded_videos" not in args:
            raise ValueError("transcoded_videos is required")
        if "video_bitrate_mbps" not in args or args["video_bitrate_mbps"] is None:
            raise ValueError("video_bitrate_mbps is required for VBR mode")
        if "minrate_mbps" not in args or args["minrate_mbps"] is None:
            raise ValueError("minrate_mbps is required for VBR mode")
        if "maxrate_mbps" not in args or args["maxrate_mbps"] is None:
            raise ValueError("maxrate_mbps is required for VBR mode")
        if "bufsize_mbps" not in args or args["bufsize_mbps"] is None:
            raise ValueError("bufsize_mbps is required for VBR mode")

        videos_path = Path(args["videos"])
        if not videos_path.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{videos_path}'")

    def get_output_subdir(self) -> str:
        return settings.output_subdirs.video

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        filename = f"{self.series_name}_{episode_info.episode_code()}{DEFAULT_VIDEO_EXTENSION}"
        output_path = self._build_season_path(episode_info, filename)
        return [OutputSpec(path=output_path, required=True)]

    def _get_temp_files(self, item: ProcessingItem) -> List[str]:
        expected_outputs = self._get_expected_outputs(item)
        if not expected_outputs:
            return []
        temp_path = expected_outputs[0].path.with_suffix('.mp4.tmp')
        return [str(temp_path)]

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        video_file = item.input_path
        output_path = missing_outputs[0].path
        temp_path = output_path.with_suffix('.mp4.tmp')

        try:
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            self.__transcode_video(video_file, temp_path)
            temp_path.replace(output_path)
            self.logger.info(f"Processed: {video_file} -> {output_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg failed for {video_file}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during transcoding {video_file}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise

    def __transcode_video(self, input_video: Path, output_video: Path) -> None:
        input_fps = self.__get_framerate(input_video)
        input_video_bitrate = self.__get_video_bitrate(input_video)
        input_audio_bitrate = self.__get_audio_bitrate(input_video)

        target_fps = min(input_fps, 30.0)
        if target_fps < input_fps:
            self.logger.info(
                f"Input FPS ({input_fps}) > 30. Limiting to {target_fps} FPS for compatibility and smaller file size.",
            )

        video_bitrate = self.video_bitrate_mbps
        minrate = self.minrate_mbps
        maxrate = self.maxrate_mbps
        bufsize = self.bufsize_mbps

        if input_video_bitrate and input_video_bitrate < video_bitrate:
            adjusted_bitrate = min(input_video_bitrate * 1.05, video_bitrate)
            ratio = adjusted_bitrate / video_bitrate
            video_bitrate = adjusted_bitrate
            minrate = round(minrate * ratio, 2)
            maxrate = round(maxrate * ratio, 2)
            bufsize = round(bufsize * ratio, 2)
            self.logger.info(
                f"Input video bitrate ({input_video_bitrate} Mbps) < target ({self.video_bitrate_mbps} Mbps). "
                f"Adjusted to {video_bitrate} Mbps to avoid quality loss.",
            )

        audio_bitrate = self.audio_bitrate_kbps
        if input_audio_bitrate and input_audio_bitrate < audio_bitrate:
            adjusted_audio_bitrate = min(int(input_audio_bitrate * 1.05), audio_bitrate)
            audio_bitrate = adjusted_audio_bitrate
            self.logger.info(
                f"Input audio bitrate ({input_audio_bitrate} kbps) < target ({self.audio_bitrate_kbps} kbps). "
                f"Adjusted to {audio_bitrate} kbps to avoid quality loss.",
            )

        vf_filter = (
            "scale='iw*sar:ih',"
            f"scale={self.resolution.width}:{self.resolution.height}:force_original_aspect_ratio=decrease,"
            f"pad={self.resolution.width}:{self.resolution.height}:(ow-iw)/2:(oh-ih)/2:black,"
            "setsar=1"
        )

        command = [
            "ffmpeg",
            "-v", "error",
            "-stats",
            "-hide_banner",
            "-y",
            "-i", str(input_video),
            "-c:v", self.codec,
            "-preset", self.preset,
            "-profile:v", "main",
            "-level", "4.1",
            "-pix_fmt", "yuv420p",
        ]

        if target_fps < input_fps:
            command.extend(["-r", str(target_fps)])

        command.extend([
            "-rc", "vbr_hq",
            "-b:v", f"{video_bitrate}M",
            "-minrate", f"{minrate}M",
            "-maxrate", f"{maxrate}M",
            "-bufsize", f"{bufsize}M",
            "-bf", "2",
            "-b_adapt", "1",
            "-2pass", "1",
            "-rc-lookahead", "32",
            "-aq-strength", "15",
        ])

        command.extend([
            "-g", str(int(target_fps * self.gop_size)),
            "-spatial-aq", "1",
            "-temporal-aq", "1",
            "-multipass", "fullres",
            "-c:a", "aac",
            "-b:a", f"{audio_bitrate}k",
            "-ac", "2",
            "-vf", vf_filter,
            "-movflags", "+faststart",
            "-f", "mp4",
            str(output_video),
        ])

        self.logger.debug(f"Transcoding: {input_video.name} -> {output_video.name}")
        self.logger.debug(f"FFmpeg command: {' '.join(command)}")
        self.logger.debug(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'not set')[:200]}")

        try:
            subprocess.run(command, check=True, capture_output=False, text=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg failed with exit code: {e.returncode}")
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
        streams: List[Dict[str, Any]] = probe_data.get(FfprobeKeys.STREAMS, [])
        if not streams:
            raise ValueError(f"No video streams found in {video}")
        r_frame_rate: Optional[str] = streams[0].get(FfprobeStreamKeys.R_FRAME_RATE)
        if not r_frame_rate:
            raise ValueError(f"Frame rate not found in {video}")
        num, denom = [int(x) for x in r_frame_rate.split("/")]

        return num / denom

    @staticmethod
    def __get_video_bitrate(video: Path) -> Optional[float]:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=bit_rate",
            "-of", "json",
            str(video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data: Dict[str, Any] = json.loads(result.stdout)
        streams: List[Dict[str, Any]] = probe_data.get(FfprobeKeys.STREAMS, [])
        if not streams:
            return None
        bit_rate = streams[0].get(FfprobeStreamKeys.BIT_RATE)
        if not bit_rate:
            return None
        return round(int(bit_rate) / 1_000_000, 2)

    @staticmethod
    def __get_audio_bitrate(video: Path) -> Optional[int]:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=bit_rate",
            "-of", "json",
            str(video),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe_data: Dict[str, Any] = json.loads(result.stdout)
        streams: List[Dict[str, Any]] = probe_data.get(FfprobeKeys.STREAMS, [])
        if not streams:
            return None
        bit_rate = streams[0].get(FfprobeStreamKeys.BIT_RATE)
        if not bit_rate:
            return None
        return int(int(bit_rate) / 1000)
