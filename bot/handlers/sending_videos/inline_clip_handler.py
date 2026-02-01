from pathlib import Path
import tempfile
from typing import List
from uuid import uuid4

from aiogram import Bot
from aiogram.types import (
    FSInputFile,
    InlineQueryResultArticle,
    InlineQueryResultCachedVideo,
    InputTextMessageContent,
)

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.search.transcription_finder import TranscriptionFinder
from bot.settings import settings
from bot.utils.functions import format_segment
from bot.utils.log import log_user_activity
from bot.video.clips_extractor import ClipsExtractor
from bot.video.utils import FFMpegException


class InlineClipHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return []

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    async def _do_handle(self) -> None:
        raise NotImplementedError("InlineClipHandler should use handle_inline() instead of handle()")

    async def handle_inline(self, query: str, bot: Bot, user_id: int) -> List:
        await log_user_activity(user_id, f"Inline query: {query}", self._logger)

        if not query.strip():
            return []

        if not settings.INLINE_CACHE_CHANNEL_ID:
            result = InlineQueryResultArticle(
                id=str(uuid4()),
                title="Inline mode nie jest skonfigurowany",
                description="Skontaktuj się z administratorem",
                input_message_content=InputTextMessageContent(
                    message_text="Inline mode wymaga konfiguracji INLINE_CACHE_CHANNEL_ID",
                ),
            )
            return [result]

        results = []

        saved_clip = await DatabaseManager.get_clip_by_name(user_id, query.strip())
        if saved_clip:
            temp_file = Path(tempfile.gettempdir()) / f"saved_clip_{saved_clip.id}.mp4"
            temp_file.write_bytes(saved_clip.video_data)

            try:
                sent_message = await bot.send_video(
                    chat_id=settings.INLINE_CACHE_CHANNEL_ID,
                    video=FSInputFile(temp_file),
                    supports_streaming=True,
                )
                temp_file.unlink()

                results.append(
                    InlineQueryResultCachedVideo(
                        id=str(uuid4()),
                        video_file_id=sent_message.video.file_id,
                        title=f"💾 Zapisany klip: {saved_clip.name}",
                        description=f"Sezon {saved_clip.season}, Odcinek {saved_clip.episode_number} | Czas: {saved_clip.duration:.1f}s",
                    ),
                )
            except Exception as e:
                self._logger.error(f"Error uploading saved clip: {e}")
                if temp_file.exists():
                    temp_file.unlink()

        segments = await TranscriptionFinder.find_segment_by_quote(query, self._logger, return_all=True)

        if segments:
            season_info = await TranscriptionFinder.get_season_details_from_elastic(logger=self._logger)

            for i, segment in enumerate(segments[:5], start=1):
                segment_info = format_segment(segment, season_info)

                start_time = max(0, segment["start"] - settings.EXTEND_BEFORE)
                end_time = segment["end"] + settings.EXTEND_AFTER
                clip_duration = end_time - start_time

                if not await DatabaseManager.is_admin_or_moderator(
                        user_id,
                ) and clip_duration > settings.MAX_CLIP_DURATION:
                    continue

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

                    output_filename.unlink()

                    results.append(
                        InlineQueryResultCachedVideo(
                            id=str(uuid4()),
                            video_file_id=sent_message.video.file_id,
                            title=f"{i}. {segment_info.episode_formatted} | {segment_info.time_formatted}",
                            description=f"{segment_info.episode_title}",
                        ),
                    )

                except FFMpegException as e:
                    self._logger.error(f"Error generating clip for segment {segment['id']}: {e}")
                    continue

        if not results:
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f'Nie znaleziono klipu dla: "{query}"',
                    description="Spróbuj innego wyszukiwania",
                    input_message_content=InputTextMessageContent(
                        message_text=f"Nie znaleziono klipu dla: {query}",
                    ),
                ),
            )

        await DatabaseManager.log_command_usage(user_id)
        self._logger.info(f"Inline query handled for user {user_id}: '{query}' - {len(results)} results")

        return results
