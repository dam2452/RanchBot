import logging
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
    InputTextMessageContent,
)

from bot.database.database_manager import DatabaseManager
from bot.database.models import VideoClip
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.bot_message_handler_responses import get_general_error_message
from bot.responses.sending_videos.clip_handler_responses import get_no_quote_provided_message
from bot.search.transcription_finder import TranscriptionFinder
from bot.settings import settings
from bot.utils.functions import format_segment
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

    async def handle_inline(self, query: str, bot: Bot, user_id: int) -> List[InlineQueryResult]:
        try:  # pylint: disable=too-many-try-statements
            await log_user_activity(user_id, f"Inline query: {query}", self._logger)
            if not query.strip():
                return []

            saved_clip, segments_to_send = await self.__get_clips_to_send(user_id, query.strip())

            if not saved_clip and not segments_to_send:
                return [self.__create_no_results_response(query)]

            results: List[InlineQueryResult] = []

            if saved_clip:
                saved_clip_result = await self.__upload_saved_clip_to_cache(saved_clip, bot)
                if saved_clip_result:
                    results.append(saved_clip_result)

            if segments_to_send:
                season_info = await TranscriptionFinder.get_season_details_from_elastic(logger=self._logger)
                await log_system_message(logging.INFO, f"Processing {len(segments_to_send)} segments for inline", self._logger)
                for i, segment in enumerate(segments_to_send, start=1):
                    result = await self.__create_segment_result(user_id, segment, i, season_info, bot)
                    if result:
                        results.append(result)
                    else:
                        await log_system_message(logging.WARNING, f"Segment {i} returned None result", self._logger)

            await log_system_message(logging.INFO, f"Total results generated: {len(results)}", self._logger)
            if not results:
                await log_system_message(logging.WARNING, "No results, returning no_results_response", self._logger)
                return [self.__create_no_results_response(query)]

            await log_system_message(logging.INFO, "Logging command usage", self._logger)
            await DatabaseManager.log_command_usage(user_id)

            await log_system_message(logging.INFO, f"Inline query handled for user {user_id}: '{query}' - {len(results)} results", self._logger)

            return results

        except Exception as e:
            await log_system_message(
                logging.ERROR,
                f"{type(e)} Error in inline query for user '{user_id}': {e}",
                self._logger,
            )
            return [self.__create_error_response()]

    async def __get_clips_to_send(
        self,
        user_id: int,
        query: str,
    ) -> Tuple[Optional[VideoClip], List[dict]]:
        saved_clip = await DatabaseManager.get_clip_by_name(user_id, query)

        search_count = 4 if saved_clip else 5
        segments = await TranscriptionFinder.find_segment_by_quote(query, self._logger, return_all=True)
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
            sent_message = await bot.send_video(
                chat_id=settings.INLINE_CACHE_CHANNEL_ID,
                video=FSInputFile(temp_file),
                supports_streaming=True,
            )

            return InlineQueryResultCachedVideo(
                id=str(uuid4()),
                video_file_id=sent_message.video.file_id,
                title=f"💾 Zapisany klip: {saved_clip.name}",
                description=f"Sezon {saved_clip.season}, Odcinek {saved_clip.episode_number} | Czas: {saved_clip.duration:.1f}s",
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

            sent_message = await bot.send_video(
                chat_id=settings.INLINE_CACHE_CHANNEL_ID,
                video=FSInputFile(output_filename),
                supports_streaming=True,
            )

            if not sent_message or not sent_message.video or not sent_message.video.file_id:
                await log_system_message(logging.ERROR, f"Invalid sent_message for segment {index}: sent_message={sent_message}", self._logger)
                return None

            return InlineQueryResultCachedVideo(
                id=str(uuid4()),
                video_file_id=sent_message.video.file_id,
                title=f"{index}. {segment_info.episode_formatted} | {segment_info.time_formatted}",
                description=f"{segment_info.episode_title}",
            )

        except Exception as e:
            self._logger.error(f"Error creating segment result for segment {segment.get('id', 'unknown')}: {type(e).__name__}: {e}")
            return None
        finally:
            if output_filename and output_filename.exists():
                output_filename.unlink()

    @staticmethod
    def __create_no_results_response(query: str) -> InlineQueryResultArticle:
        return InlineQueryResultArticle(
            id=str(uuid4()),
            title=f'Nie znaleziono klipu dla: "{query}"',
            description="Spróbuj innego wyszukiwania",
            input_message_content=InputTextMessageContent(
                message_text=f"Nie znaleziono klipu dla: {query}",
            ),
        )

    @staticmethod
    def __create_error_response() -> InlineQueryResultArticle:
        return InlineQueryResultArticle(
            id=str(uuid4()),
            title="Wystąpił błąd",
            description="Spróbuj ponownie później",
            input_message_content=InputTextMessageContent(
                message_text=get_general_error_message(),
            ),
        )
