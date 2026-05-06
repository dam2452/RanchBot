import asyncio
import os
from pathlib import Path
import tempfile
from typing import Optional

from bot.video.utils import run_ffmpeg_command


class KeyframeExtractor:

    @staticmethod
    async def extract_keyframe(video_path: Path, seek_time: float) -> Path:
        fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        output_path = Path(tmp_path)

        pre_seek = max(0.0, seek_time - 2.0)
        command = [
            "ffmpeg", "-y",
            "-ss", str(pre_seek),
            "-i", str(video_path),
            "-ss", str(seek_time - pre_seek),
            "-vframes", "1",
            "-q:v", "2",
            "-loglevel", "error",
            str(output_path),
        ]

        await run_ffmpeg_command(command)
        return output_path

    @staticmethod
    async def extract_thumbnail_bytes(video_path: Path, start_time: float, duration: float) -> Optional[bytes]:
        try:
            seek_time = start_time + duration * 0.1
            frame_path = await KeyframeExtractor.extract_keyframe(video_path, seek_time)
            thumbnail_data = frame_path.read_bytes()
            frame_path.unlink(missing_ok=True)
            return thumbnail_data
        except Exception:
            return None

    @staticmethod
    async def get_keyframe_timestamps(video_path: Path, start_time: float, end_time: float) -> list[float]:
        command = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-skip_frame", "noref",
            "-show_entries", "packet=pts_time,flags",
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
            parts = line.strip().split(",")
            if len(parts) < 2 or "K" not in parts[1]:
                continue
            try:
                ts = float(parts[0])
                if start_time <= ts <= end_time:
                    timestamps.append(ts)
            except ValueError:
                continue

        return timestamps
