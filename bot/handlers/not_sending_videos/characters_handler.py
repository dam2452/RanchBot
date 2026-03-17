import json
import logging
import math
from typing import (
    List,
    Optional,
)

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import ValidatorFunctions
from bot.handlers.character_bot_handler import CharacterBotHandler
from bot.responses.not_sending_videos.characters_handler_responses import (
    format_character_scenes,
    format_character_scenes_full,
    format_characters_list,
    format_characters_list_full,
    get_invalid_args_count_message,
    get_log_character_scenes_message,
    get_log_characters_list_message,
    get_no_characters_message,
    scene_to_search_segment,
)
from bot.search.video_frames import CharacterFinder
from bot.settings import settings as s
from bot.types import CharacterScene


class CharactersHandler(CharacterBotHandler):
    def get_commands(self) -> List[str]:
        return ["postacie", "characters", "p", "pl", "postacie_lista"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_invalid_args_count_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 0, math.inf)

    async def _do_handle(self) -> None:
        text_parts = self._message.get_text().split()
        command = text_parts[0].lstrip("/").lower()
        args = text_parts[1:]
        is_full = command in {"pl", "postacie_lista"}
        user_id = self._message.get_user_id()
        series_name = await self._get_user_active_series(user_id)

        if not args:
            await self.__handle_list_mode(series_name, is_full)
            return

        character, emotion_input, emotion_en = await self._find_character(args, series_name)
        if character is None:
            return

        if emotion_en:
            await self.__handle_character_emotion_mode(character, emotion_input, emotion_en, series_name, is_full)
        else:
            await self.__handle_character_mode(character, series_name, is_full)

    async def __handle_list_mode(self, series_name: str, is_full: bool) -> None:
        characters = await CharacterFinder.get_all_characters(series_name=series_name, logger=self._logger)
        if not characters:
            await self._reply_error(get_no_characters_message())
            return
        if is_full:
            await self._send_document(
                format_characters_list_full(characters),
                f"{s.BOT_USERNAME}_Postacie.txt",
                "Pełna lista postaci",
            )
        else:
            await self._reply(format_characters_list(characters))
        await self._log_system_message(
            logging.INFO,
            get_log_characters_list_message(len(characters), self._message.get_username()),
        )

    async def __handle_character_mode(self, character_name: str, series_name: str, is_full: bool) -> None:
        scenes = await CharacterFinder.get_scenes_by_character(
            character_name=character_name,
            series_name=series_name,
            logger=self._logger,
        )
        await self.__save_scenes_to_last_search(scenes, character_name)
        if is_full:
            await self._send_document(
                format_character_scenes_full(character_name, scenes),
                f"{s.BOT_USERNAME}_Sceny_{self._sanitize_filename(character_name)}.txt",
                f"Pełna lista scen: {character_name}",
            )
        else:
            await self._reply(format_character_scenes(character_name, scenes))
        await self._log_system_message(
            logging.INFO,
            get_log_character_scenes_message(character_name, len(scenes), self._message.get_username()),
        )

    async def __handle_character_emotion_mode(
        self,
        character_name: str,
        emotion_input: str,
        emotion_en: str,
        series_name: str,
        is_full: bool,
    ) -> None:
        scenes = await CharacterFinder.get_scenes_by_character_and_emotion(
            character_name=character_name,
            emotion_en=emotion_en,
            series_name=series_name,
            logger=self._logger,
        )
        await self.__save_scenes_to_last_search(scenes, character_name, emotion_input)
        if is_full:
            await self._send_document(
                format_character_scenes_full(character_name, scenes, emotion_filter=emotion_input),
                f"{s.BOT_USERNAME}_Sceny_{self._sanitize_filename(character_name)}_{emotion_en}.txt",
                f"Pełna lista scen: {character_name} ({emotion_input})",
            )
        else:
            await self._reply(format_character_scenes(character_name, scenes, emotion_filter=emotion_input))
        await self._log_system_message(
            logging.INFO,
            get_log_character_scenes_message(character_name, len(scenes), self._message.get_username()),
        )

    async def __save_scenes_to_last_search(
        self,
        scenes: List[CharacterScene],
        character_name: str,
        emotion_input: Optional[str] = None,
    ) -> None:
        if not scenes:
            return
        segments = [scene_to_search_segment(scene) for scene in scenes]
        quote = f"{character_name} {emotion_input}" if emotion_input else character_name
        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=quote,
            segments=json.dumps(segments),
        )
