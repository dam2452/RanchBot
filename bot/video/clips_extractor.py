import asyncio
import logging
from pathlib import Path
import tempfile

from bot.utils.log import log_system_message
from bot.video.utils import (
    FFMpegException,
    get_video_duration,
)


class ClipsExtractor:
    @staticmethod
    async def extract_clip(
        video_path: Path,
        start_time: float,
        end_time: float,
        logger: logging.Logger,
    ) -> Path:
        duration = end_time - start_time
        output_filename = Path(tempfile.mktemp(suffix=".mp4"))
        await log_system_message(
            logging.INFO,
            f"Extracting clip from {video_path}, start: {start_time}, end: {end_time}, duration: {duration}",
            logger,
        )

        command = [
            "ffmpeg",
            "-y",  # overwrite output files
            "-ss", str(start_time),
            "-i", str(video_path),
            "-t", str(duration),
            "-c", "copy",
            "-movflags", "+faststart",
            "-fflags", "+genpts",
            "-avoid_negative_ts", "1",
            "-loglevel", "error",
            str(output_filename),
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, stderr = await process.communicate()

        if process.returncode != 0:
            raise FFMpegException(stderr.decode())

        await log_system_message(
            logging.INFO,
            f"Clip extracted successfully: {output_filename}",
            logger,
        )

        clip_duration = await get_video_duration(output_filename)
        await log_system_message(logging.INFO, f"Clip duration: {clip_duration}", logger)
        return output_filename
