import json
import logging
from pathlib import Path
import subprocess

from bot.utils.resolution import Resolution
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class VideoTranscoder:
    DEFAULT_OUTPUT_DIR: Path = "transcoded_videos"
    DEFAULT_RESOLUTION: Resolution = Resolution.R1080P
    DEFAULT_CODEC: str = "h264_nvenc"
    DEFAULT_PRESET: str = "slow"
    DEFAULT_CRF: int = 31
    DEFAULT_GOP_SIZE: float = 0.5


    def __init__(self, args: json):
        self.__input_videos: Path = Path(args["input_videos"])
        self.__output_videos: Path = Path(args["transcoded_videos"])
        self.__resolution: Resolution = Resolution.from_str(args["resolution"])

        self.__codec: str = str(args["codec"])
        self.__preset: str = str(args["preset"])
        self.__crf: int = int(args["crf"])
        self.__gop_size: float = float(args["gop_size"])

        if not self.__input_videos.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{self.__input_videos}'")

        self.__output_videos.mkdir(parents=True, exist_ok=True)

        self.logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=3,
        )


    def work(self) -> int:
        for video_file in self.__input_videos.rglob("*.mp4"):
            output_path = self.__output_videos / video_file.relative_to(self.__input_videos)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                self.__process_video(video_file, output_path)
            except Exception as e: # pylint: disable=broad-exception-caught
                self.logger.error(f"Error processing video {video_file}: {e}")

        return self.logger.finalize()

    def __process_video(self, video: Path, output: Path) -> None:
        fps = self.__get_framerate(video)

        vf_filter = (
            f"scale={self.__resolution.width}:{self.__resolution.height}:force_original_aspect_ratio=decrease,"
            f"pad={self.__resolution.width}:{self.__resolution.height}:(ow-iw)/2:(oh-ih)/2:black"
        )

        command = [
            "ffmpeg",
            "-y",
            "-i", str(video),
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
            str(output),
        ]

        self.logger.info(f"Processing [{self.__resolution}]: {video} -> {output}")
        subprocess.run(command, check=True)

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

        probe_data = json.loads(result.stdout)
        streams = probe_data.get("streams")
        if not streams:
            raise ValueError(f"No video streams found in {video}")

        r_frame_rate = streams[0].get("r_frame_rate")
        if not r_frame_rate:
            raise ValueError(f"Frame rate not found in {video}")

        num, denom = (int(x) for x in r_frame_rate.split('/'))
        return num / denom
