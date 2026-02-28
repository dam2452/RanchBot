import json
import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.models import ClipType
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.characters_handler_responses import scene_to_search_segment
from bot.responses.not_sending_videos.emotions_handler_responses import map_emotion_to_en
from bot.responses.sending_videos.character_clip_handler_responses import (
    get_log_character_clip_message,
    get_no_quote_provided_message,
    get_no_scenes_found_message,
    get_no_video_path_message,
)
from bot.search.character_finder import CharacterFinder
from bot.services.scene_snap.scene_snap_service import SceneSnapService
from bot.settings import settings
from bot.utils.constants import SegmentKeys
from bot.video.clips_extractor import ClipsExtractor


class CharacterClipHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["klip_postac", "kp"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_no_quote_provided_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, 2)

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()[1:]
        user_id = self._message.get_user_id()
        series_name = await self._get_user_active_series(user_id)

        character = await CharacterFinder.find_best_matching_name(args[0], series_name, self._logger)
        if character is None:
            await self._reply_error(f"Nie znaleziono postaci pasujacych do '{args[0]}'.")
            return

        emotion_input = args[1] if len(args) > 1 else ""
        emotion_en = ""
        if emotion_input:
            emotion_en = map_emotion_to_en(emotion_input) or ""
            if not emotion_en:
                await self._reply_error(
                    f"Nieznana emocja: '{emotion_input}'. Uzyj /emocje aby zobaczyc liste dostepnych emocji.",
                )
                return

        if emotion_en:
            scenes = await CharacterFinder.get_scenes_by_character_and_emotion(
                character_name=character,
                emotion_en=emotion_en,
                series_name=series_name,
                logger=self._logger,
            )
        else:
            scenes = await CharacterFinder.get_scenes_by_character(
                character_name=character,
                series_name=series_name,
                logger=self._logger,
            )

        if not scenes:
            await self._reply_error(get_no_scenes_found_message(character, emotion_input))
            return

        segments = [scene_to_search_segment(scene) for scene in scenes]
        quote = f"{character} {emotion_input}".strip()
        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=quote,
            segments=json.dumps(segments),
        )

        top_segment = segments[0]
        if not top_segment.get(SegmentKeys.VIDEO_PATH):
            await self._reply_error(get_no_video_path_message())
            return

        start_time = max(0, top_segment[SegmentKeys.START_TIME] - settings.EXTEND_BEFORE)
        end_time = top_segment[SegmentKeys.END_TIME] + settings.EXTEND_AFTER

        start_time, end_time = await SceneSnapService.snap_clip_times(
            series_name, top_segment, start_time, end_time, self._logger,
        )

        clip_duration = end_time - start_time
        if await self._handle_clip_duration_limit_exceeded(clip_duration):
            return

        output_filename = await ClipsExtractor.extract_clip(
            top_segment[SegmentKeys.VIDEO_PATH], start_time, end_time, self._logger,
        )

        await self._responder.send_video(
            output_filename,
            duration=clip_duration,
            suggestions=["Uzyj /w N aby wybrac inny wynik"],
        )

        await DatabaseManager.insert_last_clip(
            chat_id=self._message.get_chat_id(),
            segment=top_segment,
            compiled_clip=None,
            clip_type=ClipType.SINGLE,
            adjusted_start_time=start_time,
            adjusted_end_time=end_time,
            is_adjusted=False,
        )

        await self._log_system_message(
            logging.INFO,
            get_log_character_clip_message(character, self._message.get_username()),
        )
