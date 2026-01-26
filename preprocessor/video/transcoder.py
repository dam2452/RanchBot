import json
import os
from pathlib import Path
import subprocess
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.core.base_processor import (
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.constants import DEFAULT_VIDEO_EXTENSION
from preprocessor.core.output_path_builder import OutputPathBuilder
from preprocessor.utils.resolution import Resolution
from preprocessor.video.base_video_processor import BaseVideoProcessor


class VideoTranscoder(BaseVideoProcessor):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=3,
            input_videos_key="videos",
        )

        self.resolution: Resolution = self._args["resolution"]
        self.codec: str = str(self._args["codec"])
        self.preset: str = str(self._args["preset"])
        self.crf: int = int(self._args["crf"])
        self.gop_size: float = float(self._args["gop_size"])

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "videos" not in args:
            raise ValueError("videos path is required")
        if "resolution" not in args:
            raise ValueError("resolution is required")
        if "codec" not in args:
            raise ValueError("codec is required")
        if "preset" not in args:
            raise ValueError("preset is required")
        if "crf" not in args:
            raise ValueError("crf is required")
        if "gop_size" not in args:
            raise ValueError("gop_size is required")
        if "transcoded_videos" not in args:
            raise ValueError("transcoded_videos is required")

        videos_path = Path(args["videos"])
        if not videos_path.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{videos_path}'")

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        episode_info = item.metadata["episode_info"]
        output_path = OutputPathBuilder.build_video_path(episode_info, self.series_name, extension=DEFAULT_VIDEO_EXTENSION)
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
            self._transcode_video(video_file, temp_path)
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

    def _transcode_video(self, input_video: Path, output_video: Path) -> None:
        fps = self._get_framerate(input_video)

        vf_filter = (
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
            "-profile:v", "high",
            "-cq:v", str(self.crf),
            "-g", str(int(fps * self.gop_size)),
            "-spatial-aq", "1",
            "-temporal-aq", "1",
            "-rc-lookahead", "32",
            "-multipass", "fullres",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ac", "2",
            "-vf", vf_filter,
            "-movflags", "+faststart",
            "-f", "mp4",
            str(output_video),
        ]

        self.logger.debug(f"Transcoding: {input_video.name} -> {output_video.name}")
        self.logger.debug(f"FFmpeg command: {' '.join(command)}")
        self.logger.debug(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'not set')[:200]}")

        try:
            subprocess.run(command, check=True, capture_output=False, text=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg failed with exit code: {e.returncode}")
            raise

    @staticmethod
    def _get_framerate(video: Path) -> float:
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
