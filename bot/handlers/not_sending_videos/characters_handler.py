import logging
from typing import List

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.characters_handler_responses import (
    format_character_scenes,
    format_characters_list,
    get_invalid_args_count_message,
    get_log_character_scenes_message,
    get_log_characters_list_message,
    get_no_characters_message,
)
from bot.responses.not_sending_videos.emotions_handler_responses import map_emotion_to_en
from bot.search.character_finder import CharacterFinder


class CharactersHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["postacie", "characters", "p"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_invalid_args_count_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 0, 2)

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()[1:]
        user_id = self._message.get_user_id()
        series_name = await self._get_user_active_series(user_id)

        if not args:
            await self.__handle_list_mode(series_name)
        elif len(args) == 1:
            await self.__handle_character_mode(args[0], series_name)
        else:
            await self.__handle_character_emotion_mode(args[0], args[1], series_name)

    async def __handle_list_mode(self, series_name: str) -> None:
        characters = await CharacterFinder.get_all_characters(
            series_name=series_name,
            logger=self._logger,
        )
        if not characters:
            await self._reply_error(get_no_characters_message())
            return
        response = format_characters_list(characters)
        await self._reply(response)
        await self._log_system_message(
            logging.INFO,
            get_log_characters_list_message(len(characters), self._message.get_username()),
        )

    async def __handle_character_mode(self, character_name: str, series_name: str) -> None:
        scenes = await CharacterFinder.get_scenes_by_character(
            character_name=character_name,
            series_name=series_name,
            logger=self._logger,
        )
        response = format_character_scenes(character_name, scenes)
        await self._reply(response)
        await self._log_system_message(
            logging.INFO,
            get_log_character_scenes_message(character_name, len(scenes), self._message.get_username()),
        )

    async def __handle_character_emotion_mode(
        self,
        character_name: str,
        emotion_input: str,
        series_name: str,
    ) -> None:
        emotion_en = map_emotion_to_en(emotion_input)
        if not emotion_en:
            await self._reply_error(
                f"Nieznana emocja: '{emotion_input}'. Uzyj /emocje aby zobaczyc liste dostepnych emocji.",
            )
            return
        scenes = await CharacterFinder.get_scenes_by_character_and_emotion(
            character_name=character_name,
            emotion_en=emotion_en,
            series_name=series_name,
            logger=self._logger,
        )
        response = format_character_scenes(character_name, scenes, emotion_filter=emotion_input)
        await self._reply(response)
        await self._log_system_message(
            logging.INFO,
            get_log_character_scenes_message(character_name, len(scenes), self._message.get_username()),
        )
