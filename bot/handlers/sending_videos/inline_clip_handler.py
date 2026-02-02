import asyncio
import logging
import math
from pathlib import Path
import shutil
import tempfile
from typing import (
    List,
    Optional,
    Tuple,
    Union,
)
from uuid import uuid4
import zipfile

from aiogram import Bot
from aiogram.types import (
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
            self._message, 1, get_no_quote_provided_message(), math.inf,
        )

    async def _do_handle(self) -> None:
        query = " ".join(self._message.get_text().split()[1:])
        user_id = self._message.get_user_id()

        saved_clip, segments, season_info, _ = await self.__fetch_data(user_id, query)

        if not saved_clip and not segments:
            await self._answer(f'Nie znaleziono klipów dla zapytania: "{query}"')
            return

        temp_dir = Path(tempfile.mkdtemp())
        try:
            video_files = await self.__extract_clips_to_files(
                saved_clip, segments, season_info, temp_dir, is_admin=True,
            )

            if not video_files:
                await self._answer(f'Nie udało się wygenerować klipów dla zapytania: "{query}"')
                return

            zip_path = await self.__create_zip(video_files, temp_dir, query)
            await self._answer_document(
                zip_path, f'Wyniki inline dla: "{query}" ({len(video_files)} klipów)', cleanup_dir=temp_dir,
            )
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    async def handle_inline(self, bot: Bot) -> List[InlineQueryResult]:
        query = self._message.get_text().strip()
        user_id = self._message.get_user_id()

        await log_user_activity(user_id, f"Inline query: {query}", self._logger)

        if not query:
            return []

        saved_clip, segments, season_info, is_admin = await self.__fetch_data(user_id, query)

        if not saved_clip and not segments:
            await log_system_message(logging.INFO, f"No results for inline query: '{query}'", self._logger)
            return [generate_error_result(f'Nie znaleziono klipu dla: "{query}"')]

        results = await self.__create_inline_results(saved_clip, segments, season_info, bot, is_admin)

        if not results:
            await log_system_message(logging.ERROR, f"Failed to generate any results for: '{query}'", self._logger)
            return [generate_error_result(f'Nie znaleziono klipu dla: "{query}"')]

        await DatabaseManager.log_command_usage(user_id)
        return results

    async def __fetch_data(
        self, user_id: int, query: str,
    ) -> Tuple[Optional[VideoClip], List[dict], Optional[dict], bool]:
        saved_clip_result, segments_result, season_info_result, is_admin_result = await asyncio.gather(
            DatabaseManager.get_clip_by_name(user_id, query),
            TranscriptionFinder.find_segment_by_quote(query, self._logger, size=5),
            TranscriptionFinder.get_season_details_from_elastic(logger=self._logger),
            DatabaseManager.is_admin_or_moderator(user_id),
            return_exceptions=True,
        )

        saved_clip = saved_clip_result if not isinstance(saved_clip_result, Exception) else None
        segments = segments_result if not isinstance(segments_result, Exception) else []
        season_info = season_info_result if not isinstance(season_info_result, Exception) else None
        is_admin = is_admin_result if not isinstance(is_admin_result, Exception) else False

        segments_to_send = segments[: 4 if saved_clip else 5] if segments else []

        return saved_clip, segments_to_send, season_info, is_admin

    async def __extract_clips_to_files(
        self,
        saved_clip: Optional[VideoClip],
        segments: List[dict],
        season_info: Optional[dict],
        temp_dir: Path,
        is_admin: bool,
    ) -> List[Path]:
        video_files = []

        if saved_clip:
            saved_file = temp_dir / f"1_saved_{saved_clip.name}.mp4"
            saved_file.write_bytes(saved_clip.video_data)
            video_files.append(saved_file)

        for idx, segment in enumerate(segments, start=2 if saved_clip else 1):
            start_time = max(0, segment["start"] - settings.EXTEND_BEFORE)
            end_time = segment["end"] + settings.EXTEND_AFTER
            duration = end_time - start_time

            if not is_admin and duration > settings.MAX_CLIP_DURATION:
                continue

            try:
                segment_info = format_segment(segment, season_info) if season_info else None
                episode_code = segment_info.episode_formatted if segment_info else str(idx)

                output_path = await ClipsExtractor.extract_clip(
                    segment["video_path"], start_time, end_time, self._logger,
                )
                final_path = temp_dir / f"{idx}_search_{episode_code}.mp4"
                output_path.rename(final_path)
                video_files.append(final_path)
            except FFMpegException as e:
                await log_system_message(
                    logging.ERROR, f"FFmpeg error for segment {segment.get('id', 'unknown')}: {e}", self._logger,
                )

        return video_files

    async def __create_inline_results(
        self,
        saved_clip: Optional[VideoClip],
        segments: List[dict],
        season_info: Optional[dict],
        bot: Bot,
        is_admin: bool,
    ) -> List[InlineQueryResult]:
        results = []

        if saved_clip:
            saved_result = await self.__upload_saved_clip(saved_clip, bot)
            if saved_result:
                results.append(saved_result)

        if segments and season_info:
            segment_results = await asyncio.gather(
                *[self.__upload_segment(seg, i, season_info, bot, is_admin) for i, seg in enumerate(segments, 1)],
                return_exceptions=True,
            )

            for result in segment_results:
                if isinstance(result, Exception):
                    await log_system_message(logging.ERROR, f"Error creating segment result: {result}", self._logger)
                elif result:
                    results.append(result)

        return results

    async def __upload_segment(
        self, segment: dict, index: int, season_info: dict, bot: Bot, is_admin: bool,
    ) -> Optional[InlineQueryResultCachedVideo]:
        start_time = max(0, segment["start"] - settings.EXTEND_BEFORE)
        end_time = segment["end"] + settings.EXTEND_AFTER
        duration = end_time - start_time

        if not is_admin and duration > settings.MAX_CLIP_DURATION:
            return None

        video_path = None
        try:
            video_path = await ClipsExtractor.extract_clip(segment["video_path"], start_time, end_time, self._logger)

            segment_info = format_segment(segment, season_info)
            return await self.__cache_video(
                f"{index}. {segment_info.episode_formatted} | {segment_info.time_formatted}",
                segment_info.episode_title,
                video_path,
                bot,
            )
        except Exception as e:
            await log_system_message(
                logging.ERROR,
                f"Clip {index} failed for segment {segment.get('id', 'unknown')}: {type(e).__name__}: {e}",
                self._logger,
            )
            return None
        finally:
            if video_path and video_path.exists():
                await asyncio.to_thread(video_path.unlink)

    async def __upload_saved_clip(self, saved_clip: VideoClip, bot: Bot) -> Optional[InlineQueryResultCachedVideo]:
        temp_file = Path(tempfile.gettempdir()) / f"saved_clip_{saved_clip.id}.mp4"
        await asyncio.to_thread(temp_file.write_bytes, saved_clip.video_data)

        try:
            return await self.__cache_video(
                f"💾 Zapisany klip: {saved_clip.name}",
                f"Sezon {saved_clip.season}, Odcinek {saved_clip.episode_number} | Czas: {saved_clip.duration:.1f}s",
                temp_file,
                bot,
            )
        except Exception as e:
            await log_system_message(logging.ERROR, f"Error uploading saved clip: {e}", self._logger)
            return None
        finally:
            if temp_file.exists():
                await asyncio.to_thread(temp_file.unlink)

    @staticmethod
    async def __cache_video(title: str, description: str, video_path: Path, bot: Bot) -> InlineQueryResultCachedVideo:
        sent_message = await bot.send_video(chat_id=settings.INLINE_CACHE_CHANNEL_ID, video=FSInputFile(video_path))
        return InlineQueryResultCachedVideo(
            id=str(uuid4()), video_file_id=sent_message.video.file_id, title=title, description=description,
        )

    @staticmethod
    async def __create_zip(video_files: List[Path], temp_dir: Path, query: str) -> Path:
        zip_path = temp_dir / f"inline_results_{query[:20]}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zipf:
            for video_file in video_files:
                zip_info = zipfile.ZipInfo(filename=video_file.name)
                zip_info.date_time = (1980, 1, 1, 0, 0, 0)
                zip_info.compress_type = zipfile.ZIP_STORED
                with open(video_file, 'rb') as f:
                    zipf.writestr(zip_info, f.read())
        return zip_path
