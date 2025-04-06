import json
import logging
from pathlib import Path
import subprocess
import re

from bot.utils.resolution import Resolution
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class VideoTranscoder:
    DEFAULT_OUTPUT_DIR: Path = Path("transcoded_videos")
    DEFAULT_RESOLUTION: Resolution = Resolution.R1080P
    DEFAULT_CODEC: str = "h264_nvenc"
    DEFAULT_PRESET: str = "slow"
    DEFAULT_CRF: int = 31
    DEFAULT_GOP_SIZE: float = 0.5

    def __init__(self, args: dict):
        self.__input_videos: Path = Path(args["videos"])
        self.__output_videos: Path = Path(args["transcoded_videos"])
        self.__resolution: Resolution = args["resolution"]

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

        self.episodes_info = None
        if "episodes_info_json" in args:
            with open(args["episodes_info_json"], "r", encoding="utf-8") as f:
                self.episodes_info = json.load(f)

    def work(self) -> int:
        video_files = list(self.__input_videos.rglob("*.mp4"))
        series_name = self.__input_videos.resolve().name.lower()

        for video_file in video_files:
            match = re.search(r"E(\d+)", video_file.stem, re.IGNORECASE)
            if not match:
                self.logger.error(f"Cannot extract episode number from {video_file.name}")
                continue

            absolute_episode = int(match.group(1))

            season_number = 1
            relative_episode = absolute_episode

            if self.episodes_info:
                found = False
                for season_str, season_data in self.episodes_info.items():
                    episodes = season_data.get("episodes", [])

                    episodes = sorted(episodes, key=lambda ep: ep["episode_number"])
                    for idx, ep in enumerate(episodes):
                        if ep["episode_number"] == absolute_episode:
                            season_number = int(season_str)
                            relative_episode = idx + 1
                            found = True
                            break
                    if found:
                        break

                if not found:
                    self.logger.error(f"Episode {absolute_episode} not found in episodes_info.json")
                    continue

            transcoded_name = f"{series_name}_S{season_number:02d}E{relative_episode:02d}.mp4"
            output_dir = self.__output_videos / f"Sezon {season_number}"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / transcoded_name

            try:
                self.__process_video(video_file, output_path)

                self.logger.info(f"Processed video: {video_file} -> {output_path}")
            except Exception as e:
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
