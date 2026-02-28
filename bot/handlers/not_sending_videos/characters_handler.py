import difflib
import logging
from pathlib import Path
import tempfile
from typing import (
    List,
    Optional,
)

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.characters_handler_responses import (
    format_character_scenes,
    format_character_scenes_full,
    format_characters_list,
    format_characters_list_full,
    get_invalid_args_count_message,
    get_log_character_scenes_message,
    get_log_characters_list_message,
    get_no_characters_message,
)
from bot.responses.not_sending_videos.emotions_handler_responses import map_emotion_to_en
from bot.search.character_finder import CharacterFinder
from bot.settings import settings as s


class CharactersHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["postacie", "characters", "p", "pl", "postacie_lista"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_invalid_args_count_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 0, 2)

    async def _do_handle(self) -> None:
        text_parts = self._message.get_text().split()
        command = text_parts[0].lstrip("/").lower()
        args = text_parts[1:]
        is_full = command in {"pl", "postacie_lista"}
        user_id = self._message.get_user_id()
        series_name = await self._get_user_active_series(user_id)

        if not args:
            await self.__handle_list_mode(series_name, is_full)
        elif len(args) == 1:
            character = await self.__resolve_character(args[0], series_name)
            if character is None:
                await self._reply_error(f"Nie znaleziono postaci pasujacych do '{args[0]}'.")
                return
            await self.__handle_character_mode(character, series_name, is_full)
        else:
            character = await self.__resolve_character(args[0], series_name)
            if character is None:
                await self._reply_error(f"Nie znaleziono postaci pasujacych do '{args[0]}'.")
                return
            emotion_en = map_emotion_to_en(args[1])
            if not emotion_en:
                await self._reply_error(
                    f"Nieznana emocja: '{args[1]}'. Uzyj /emocje aby zobaczyc liste dostepnych emocji.",
                )
                return
            await self.__handle_character_emotion_mode(character, args[1], emotion_en, series_name, is_full)

    async def __handle_list_mode(self, series_name: str, is_full: bool) -> None:
        characters = await CharacterFinder.get_all_characters(series_name=series_name, logger=self._logger)
        if not characters:
            await self._reply_error(get_no_characters_message())
            return
        if is_full:
            await self.__send_document(
                format_characters_list_full(characters),
                f"{s.BOT_USERNAME}_Postacie.txt",
                "Pelna lista postaci",
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
        if is_full:
            await self.__send_document(
                format_character_scenes_full(character_name, scenes),
                f"{s.BOT_USERNAME}_Sceny_{self.__sanitize(character_name)}.txt",
                f"Pelna lista scen: {character_name}",
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
        if is_full:
            await self.__send_document(
                format_character_scenes_full(character_name, scenes, emotion_filter=emotion_input),
                f"{s.BOT_USERNAME}_Sceny_{self.__sanitize(character_name)}_{emotion_en}.txt",
                f"Pelna lista scen: {character_name} ({emotion_input})",
            )
        else:
            await self._reply(format_character_scenes(character_name, scenes, emotion_filter=emotion_input))
        await self._log_system_message(
            logging.INFO,
            get_log_character_scenes_message(character_name, len(scenes), self._message.get_username()),
        )

    async def __send_document(self, content: str, filename: str, caption: str) -> None:
        file_path = Path(tempfile.gettempdir()) / filename
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)
        await self._responder.send_document(file_path, caption=caption)

    async def __resolve_character(self, query: str, series_name: str) -> Optional[str]:
        characters = await CharacterFinder.get_all_characters(series_name=series_name, logger=self._logger)
        return self.__fuzzy_match_name(query, [c["name"] for c in characters])

    @staticmethod
    def __fuzzy_match_name(query: str, names: List[str]) -> Optional[str]:
        name_map = {n.lower(): n for n in names}
        if query.lower() in name_map:
            return name_map[query.lower()]
        matches = difflib.get_close_matches(query.lower(), list(name_map.keys()), n=1, cutoff=0.6)
        return name_map[matches[0]] if matches else None

    @staticmethod
    def __sanitize(name: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in name).strip("_")
