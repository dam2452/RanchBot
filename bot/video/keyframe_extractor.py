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
