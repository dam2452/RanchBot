import asyncio
import math
from pathlib import Path
import tempfile
from typing import (
    List,
    Optional,
    Tuple,
    Union,
)
from uuid import uuid4

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
from bot.utils.log import log_user_activity
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
        query = self._message.get_text().split()[0]
        await log_user_activity(self._message.get_user_id(), f"Inline query: {query}", self._logger)
        if not query:
            return []

        saved_clip, segments_to_send = await self.__get_clips_to_send(self._message.get_user_id(), query)

        if not saved_clip and not segments_to_send:
            return [generate_error_result(f'Nie znaleziono klipu dla: "{query}"')]

        results: List[InlineQueryResult] = []

        if saved_clip:
            saved_clip_result = await self.__upload_saved_clip_to_cache(saved_clip, bot)
            if saved_clip_result:
                results.append(saved_clip_result)

        if segments_to_send:
            season_info = await TranscriptionFinder.get_season_details_from_elastic(logger=self._logger)

            tasks = [
                self.__create_segment_result(self._message.get_user_id(), segment, i, season_info, bot)
                for i, segment in enumerate(segments_to_send, start=1)
            ]
            segment_results = await asyncio.gather(*tasks, return_exceptions=False)

            for result in segment_results:
                if result:
                    results.append(result)

        if not results:
            return [generate_error_result(f'Nie znaleziono klipu dla: "{query}"')]

        await DatabaseManager.log_command_usage(self._message.get_user_id())
        self._logger.info(f"Inline query handled: '{query}' - {len(results)} results")

        return results


    async def __get_clips_to_send(
        self,
        user_id: int,
        query: str,
    ) -> Tuple[Optional[VideoClip], List[dict]]:
        saved_clip = await DatabaseManager.get_clip_by_name(user_id, query)

        search_count = 4 if saved_clip else 5
        segments = await TranscriptionFinder.find_segment_by_quote(query, self._logger, size=search_count)
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
        temp_file.write_bytes(saved_clip.video_data)

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
                temp_file.unlink()

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

    @staticmethod
    async def __cache_video(
            title: str,
            description: str,
            output_filename: Path,
            bot: Bot,
    ) -> InlineQueryResultCachedVideo:
        sent_message = await bot.send_video(
            chat_id=settings.INLINE_CACHE_CHANNEL_ID,
            video=FSInputFile(output_filename),
            supports_streaming=True,
        )

        return InlineQueryResultCachedVideo(
            id=str(uuid4()),
            video_file_id=sent_message.video.file_id,
            title=title,
            description=description,
        )
