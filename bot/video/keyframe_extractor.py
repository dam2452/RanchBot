import asyncio
import os
from pathlib import Path
import tempfile

from bot.video.utils import run_ffmpeg_command


class KeyframeExtractor:
    @staticmethod
    async def extract_keyframe(video_path: Path, seek_time: float) -> Path:
        fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        output_path = Path(tmp_path)

        command = [
            "ffmpeg", "-y",
            "-ss", str(seek_time),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            "-loglevel", "error",
            str(output_path),
        ]

        await run_ffmpeg_command(command)
        return output_path

    @staticmethod
    async def get_keyframe_timestamps(video_path: Path, start_time: float, end_time: float) -> list[float]:
        command = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "packet=pts_time",
            "-of", "csv=p=0",
            "-read_intervals", f"{start_time}%{end_time}",
            str(video_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()

        timestamps = []
        for line in stdout.decode().strip().splitlines():
            try:
                ts = float(line.strip())
                if start_time <= ts <= end_time:
                    timestamps.append(ts)
            except ValueError:
                continue

        return timestamps
