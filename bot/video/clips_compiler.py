import asyncio
import logging
import os
from pathlib import Path
import tempfile
from typing import (
    List,
    Optional,
)

from bot.database.database_manager import DatabaseManager
from bot.database.models import ClipType
from bot.interfaces.message import AbstractMessage
from bot.services.scene_snap.scene_snap_service import SceneSnapService
from bot.types import ClipSegment
from bot.utils.constants import (
    EpisodeMetadataKeys,
    SegmentKeys,
)
from bot.utils.log import log_system_message
from bot.video.clips_extractor import ClipsExtractor
from bot.video.utils import FFMpegException


class ClipsCompiler:
    @staticmethod
    async def __do_compile_clips(segment_files: List[Path], output_file: Path, logger: logging.Logger) -> None:
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt") as concat_file:
            concat_file_path = Path(concat_file.name)

        try:
            with concat_file_path.open("w", encoding="utf-8") as f:
                for tmp_file in segment_files:
                    f.write(f"file '{tmp_file.as_posix()}'\n")

            command = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file_path),
                "-c", "copy", "-movflags", "+faststart", "-fflags", "+genpts",
                "-avoid_negative_ts", "1", str(output_file),
            ]

            process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            _, stderr = await process.communicate()

            if process.returncode != 0:
                raise FFMpegException(f"FFmpeg error: {stderr.decode()}")

            await log_system_message(logging.INFO, f"Clips concatenated successfully into {output_file}", logger)
        except Exception as e:
            raise FFMpegException(f"Error during concatenation: {e}") from e
        finally:
            concat_file_path.unlink(missing_ok=True)

    @staticmethod
    async def __compile_clips(
        selected_clips: List[ClipSegment],
        logger: logging.Logger,
        series_name: Optional[str],
    ) -> Optional[Path]:
        temp_files = []
        try:
            for segment in selected_clips:
                start_time = segment[SegmentKeys.START_TIME]
                end_time = segment[SegmentKeys.END_TIME]

                if series_name and segment.get(EpisodeMetadataKeys.EPISODE_METADATA):
                    start_time, end_time = await SceneSnapService.snap_clip_times(
                        series_name, segment, start_time, end_time, logger,
                    )

                extracted_clip_path = await ClipsExtractor.extract_clip(segment[SegmentKeys.VIDEO_PATH], start_time, end_time, logger)
                temp_files.append(extracted_clip_path)

            fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            compiled_output_path = Path(tmp_path)
            await ClipsCompiler.__do_compile_clips(temp_files, compiled_output_path, logger)
            return compiled_output_path
        except Exception as e:
            raise FFMpegException(f"Error during clip compilation: {str(e)}") from e
        finally:
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink(missing_ok=True)
                        logger.info(f"Temporary file {temp_file} deleted.")
                except OSError as cleanup_error:
                    logger.error(f"Failed to delete temporary file {temp_file}: {cleanup_error}")

    @staticmethod
    async def __insert_to_last_clips(message: AbstractMessage, compiled_output: Path) -> None:
        with compiled_output.open("rb") as f:
            compiled_clip_data = f.read()

        await DatabaseManager.insert_last_clip(
            chat_id=message.get_chat_id(),
            segment={},
            compiled_clip=compiled_clip_data,
            clip_type=ClipType.COMPILED,
            adjusted_start_time=None,
            adjusted_end_time=None,
            is_adjusted=False,
        )

    @staticmethod
    async def compile(
        message: AbstractMessage,
        selected_segments: List[ClipSegment],
        logger: logging.Logger,
        series_name: Optional[str] = None,
    ) -> Path:
        compiled_output = await ClipsCompiler.__compile_clips(selected_segments, logger, series_name)
        await ClipsCompiler.__insert_to_last_clips(message, compiled_output)
        return compiled_output


async def process_compiled_clip(
    message: AbstractMessage,
    compiled_output: Path,
    clip_type: ClipType,
) -> None:
    with compiled_output.open("rb") as f:
        compiled_clip_data = f.read()

    await DatabaseManager.insert_last_clip(
        chat_id=message.get_chat_id(),
        segment={},
        compiled_clip=compiled_clip_data,
        clip_type=clip_type,
        adjusted_start_time=None,
        adjusted_end_time=None,
        is_adjusted=False,
    )
