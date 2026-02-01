import asyncio
import logging
import math
from pathlib import Path
import tempfile
import time
from typing import (
    List,
    Optional,
    Tuple,
    Union,
)
from uuid import uuid4

from aiogram import Bot
from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    InlineQueryResultArticle,
    InlineQueryResultCachedVideo,
)

from bot.database.database_manager import DatabaseManager
from bot.database.models import VideoClip
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.sending_videos.clip_handler_responses import get_no_quote_provided_message
from bot.search.transcription_finder import TranscriptionFinder
from bot.settings import settings
from bot.utils.functions import format_segment
from bot.utils.inline_telegram import generate_error_result
from bot.utils.log import (
    log_system_message,
    log_user_activity,
)
from bot.video.clips_extractor import ClipsExtractor
from bot.video.utils import FFMpegException

InlineQueryResult = Union[InlineQueryResultArticle, InlineQueryResultCachedVideo]


class InlineClipHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["inline"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message,
            1,
            get_no_quote_provided_message(),
            math.inf,
        )

    async def _do_handle(self) -> None:
        query = " ".join(self._message.get_text().split()[1:])
        user_id = self._message.get_user_id()

        saved_clip, segments_to_send = await self.__get_clips_to_send(user_id, query)

        if not saved_clip and not segments_to_send:
            await self._answer(f'Nie znaleziono klipów dla zapytania: "{query}"')
            return

        if saved_clip:
            await self.__send_saved_clip(saved_clip)

        for segment in segments_to_send:
            await self.__send_segment_clip(segment)

    async def handle_inline(self, bot: Bot) -> List[InlineQueryResult]:
        t_total = time.time()

        query = self._message.get_text().split()[0]
        user_id = self._message.get_user_id()
        await log_user_activity(user_id, f"Inline query: {query}", self._logger)
        if not query:
            return []

        t1 = time.time()
        saved_clip, segments_to_send = await self.__get_clips_to_send(user_id, query)
        await log_system_message(logging.INFO, f"⏱️  get_clips_to_send: {time.time() - t1:.2f}s", self._logger)

        if not saved_clip and not segments_to_send:
            return [generate_error_result(f'Nie znaleziono klipu dla: "{query}"')]

        parallel_tasks = []

        if segments_to_send:
            is_admin_task = DatabaseManager.is_admin_or_moderator(user_id)
            season_info_task = TranscriptionFinder.get_season_details_from_elastic(logger=self._logger)
            parallel_tasks.extend([is_admin_task, season_info_task])

        if saved_clip:
            saved_clip_task = self.__upload_saved_clip_to_cache(saved_clip, bot)
            parallel_tasks.append(saved_clip_task)

        if not parallel_tasks:
            return [generate_error_result(f'Nie znaleziono klipu dla: "{query}"')]

        t2 = time.time()
        parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
        await log_system_message(logging.INFO, f"⏱️  parallel_tasks (is_admin + season_info + saved_clip): {time.time() - t2:.2f}s", self._logger)

        results: List[InlineQueryResult] = []
        is_admin = None
        season_info = None

        result_idx = 0
        if segments_to_send:
            is_admin_result = parallel_results[result_idx]
            is_admin = is_admin_result if not isinstance(is_admin_result, Exception) else False
            result_idx += 1

            season_info_result = parallel_results[result_idx]
            season_info = season_info_result if not isinstance(season_info_result, Exception) else None
            result_idx += 1

        if saved_clip:
            saved_clip_result = parallel_results[result_idx]
            if not isinstance(saved_clip_result, Exception) and saved_clip_result:
                results.append(saved_clip_result)
            elif isinstance(saved_clip_result, Exception):
                self._logger.error(f"Error uploading saved clip: {saved_clip_result}")

        if segments_to_send and season_info:
            segment_tasks = [
                self.__create_segment_result_optimized(
                    user_id, segment, i, season_info, bot, is_admin,
                )
                for i, segment in enumerate(segments_to_send, start=1)
            ]
            t3 = time.time()
            segment_results = await asyncio.gather(*segment_tasks, return_exceptions=True)
            await log_system_message(logging.INFO, f"⏱️  segment generation + upload ({len(segment_tasks)} clips): {time.time() - t3:.2f}s", self._logger)

            for result in segment_results:
                if isinstance(result, Exception):
                    self._logger.error(f"Error creating segment result: {result}")
                elif result:
                    results.append(result)

        if not results:
            return [generate_error_result(f'Nie znaleziono klipu dla: "{query}"')]

        asyncio.create_task(DatabaseManager.log_command_usage(user_id))
        await log_system_message(logging.INFO, f"⏱️  TOTAL inline query: {time.time() - t_total:.2f}s - '{query}' - {len(results)} results", self._logger)

        return results


    async def __get_clips_to_send(
        self,
        user_id: int,
        query: str,
    ) -> Tuple[Optional[VideoClip], List[dict]]:
        saved_clip_task = DatabaseManager.get_clip_by_name(user_id, query)
        segments_task = TranscriptionFinder.find_segment_by_quote(query, self._logger, size=5)

        saved_clip, segments = await asyncio.gather(saved_clip_task, segments_task)

        search_count = 4 if saved_clip else 5
        segments_to_send = segments[:search_count] if segments else []

        return saved_clip, segments_to_send

    async def __send_saved_clip(self, saved_clip: VideoClip) -> None:
        temp_file = Path(tempfile.gettempdir()) / f"saved_clip_{saved_clip.id}.mp4"
        temp_file.write_bytes(saved_clip.video_data)

        try:
            await self._answer_video(temp_file)
        except Exception as e:
            self._logger.error(f"Error sending saved clip: {e}")
            if temp_file.exists():
                temp_file.unlink()

    async def __send_segment_clip(self, segment: dict) -> None:
        start_time = max(0, segment["start"] - settings.EXTEND_BEFORE)
        end_time = segment["end"] + settings.EXTEND_AFTER

        if await self._handle_clip_duration_limit_exceeded(end_time - start_time):
            return None

        try:
            output_filename = await ClipsExtractor.extract_clip(
                segment["video_path"],
                start_time,
                end_time,
                self._logger,
            )
            await self._answer_video(output_filename)
        except FFMpegException as e:
            self._logger.error(f"Error generating clip for segment {segment['id']}: {e}")

    async def __upload_saved_clip_to_cache(
        self,
        saved_clip: VideoClip,
        bot: Bot,
    ) -> Optional[InlineQueryResultCachedVideo]:
        temp_file = Path(tempfile.gettempdir()) / f"saved_clip_{saved_clip.id}.mp4"
        await asyncio.to_thread(temp_file.write_bytes, saved_clip.video_data)

        try:
            return await self.__cache_video(
                title=f"💾 Zapisany klip: {saved_clip.name}",
                description=f"Sezon {saved_clip.season}, Odcinek {saved_clip.episode_number} | Czas: {saved_clip.duration:.1f}s",
                output_filename=temp_file,
                bot=bot,
            )
        except Exception as e:
            self._logger.error(f"Error uploading saved clip: {e}")
            return None
        finally:
            if temp_file.exists():
                await asyncio.to_thread(temp_file.unlink)

    async def __create_segment_result(
        self,
        user_id: int,
        segment: dict,
        index: int,
        season_info: dict,
        bot: Bot,
    ) -> Optional[InlineQueryResultCachedVideo]:
        segment_info = format_segment(segment, season_info)

        start_time = max(0, segment["start"] - settings.EXTEND_BEFORE)
        end_time = segment["end"] + settings.EXTEND_AFTER
        clip_duration = end_time - start_time

        if not await DatabaseManager.is_admin_or_moderator(user_id) and clip_duration > settings.MAX_CLIP_DURATION:
            return None

        output_filename = None
        try:
            output_filename = await ClipsExtractor.extract_clip(
                segment["video_path"],
                start_time,
                end_time,
                self._logger,
            )

            return await self.__cache_video(
                title=f"{index}. {segment_info.episode_formatted} | {segment_info.time_formatted}",
                description=segment_info.episode_title,
                output_filename=output_filename,
                bot=bot,
            )

        except Exception as e:
            self._logger.error(f"Error creating segment result for segment {segment.get('id', 'unknown')}: {e}")
            return None
        finally:
            if output_filename and output_filename.exists():
                output_filename.unlink()

    async def __create_segment_result_optimized(
        self,
        user_id: int,
        segment: dict,
        index: int,
        season_info: dict,
        bot: Bot,
        is_admin: bool,
    ) -> Optional[InlineQueryResultCachedVideo]:
        segment_info = format_segment(segment, season_info)

        start_time = max(0, segment["start"] - settings.EXTEND_BEFORE)
        end_time = segment["end"] + settings.EXTEND_AFTER
        clip_duration = end_time - start_time

        if not is_admin and clip_duration > settings.MAX_CLIP_DURATION:
            return None

        output_filename = None
        try:
            t_ffmpeg = time.time()
            output_filename = await ClipsExtractor.extract_clip(
                segment["video_path"],
                start_time,
                end_time,
                self._logger,
            )
            ffmpeg_time = time.time() - t_ffmpeg
            file_size_mb = output_filename.stat().st_size / (1024 * 1024)

            t_read = time.time()
            file_data = await asyncio.to_thread(output_filename.read_bytes)
            read_time = time.time() - t_read

            t_upload = time.time()
            result = await self.__cache_video_from_bytes(
                title=f"{index}. {segment_info.episode_formatted} | {segment_info.time_formatted}",
                description=segment_info.episode_title,
                file_data=file_data,
                filename=output_filename.name,
                bot=bot,
            )
            upload_time = time.time() - t_upload

            await log_system_message(logging.INFO, f"⏱️  Clip {index}: size={file_size_mb:.2f}MB, ffmpeg={ffmpeg_time:.2f}s, read={read_time:.2f}s, upload={upload_time:.2f}s, total={ffmpeg_time+read_time+upload_time:.2f}s", self._logger)
            return result

        except Exception as e:
            self._logger.error(f"Error creating segment result for segment {segment.get('id', 'unknown')}: {e}")
            return None
        finally:
            if output_filename and output_filename.exists():
                await asyncio.to_thread(output_filename.unlink)

    @staticmethod
    async def __cache_video(
            title: str,
            description: str,
            output_filename: Path,
            bot: Bot,
    ) -> InlineQueryResultCachedVideo:
        file_data = await asyncio.to_thread(output_filename.read_bytes)

        sent_message = await bot.send_video(
            chat_id=settings.INLINE_CACHE_CHANNEL_ID,
            video=BufferedInputFile(file_data, filename=output_filename.name),
            supports_streaming=True,
        )

        return InlineQueryResultCachedVideo(
            id=str(uuid4()),
            video_file_id=sent_message.video.file_id,
            title=title,
            description=description,
        )

    @staticmethod
    async def __cache_video_from_bytes(
            title: str,
            description: str,
            file_data: bytes,
            filename: str,
            bot: Bot,
    ) -> InlineQueryResultCachedVideo:
        sent_message = await bot.send_video(
            chat_id=settings.INLINE_CACHE_CHANNEL_ID,
            video=BufferedInputFile(file_data, filename=filename),
            supports_streaming=True,
        )

        return InlineQueryResultCachedVideo(
            id=str(uuid4()),
            video_file_id=sent_message.video.file_id,
            title=title,
            description=description,
        )
