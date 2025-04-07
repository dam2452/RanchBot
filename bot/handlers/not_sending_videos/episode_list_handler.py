import logging
from pathlib import Path
from typing import (
    Awaitable,
    Callable,
    List,
    Optional,
    Tuple,
)

from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.interfaces.message import AbstractMessage
from bot.responses.not_sending_videos.episode_list_handler_responses import (
    format_episode_list_response,
    get_log_episode_list_sent_message,
    get_log_no_episodes_found_message,
    get_season_11_petition_message,
)
from bot.search.transcription_finder import TranscriptionFinder
from bot.settings import settings as s

isSeasonCustomFn = Callable[[dict], bool]
onCustomSeasonFn = Callable[[AbstractMessage], Awaitable[None]]


class EpisodeListHandler(BotMessageHandler):
    JSON_FLAG = "json"

    def get_commands(self) -> List[str]:
        return ["odcinki", "episodes", "o"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message,
            2,
            await self.get_response(RK.INVALID_ARGS_COUNT),
        )

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        return_json = self.JSON_FLAG in args

        try:
            args = [a for a in args if a != self.JSON_FLAG]
            season = int(args[1])
        except (IndexError, ValueError):
            await self._responder.send_text(await self.get_response(RK.INVALID_ARGS_COUNT))
            return

        season_info = await TranscriptionFinder.get_season_details_from_elastic(logger=self._logger)
        episodes = await TranscriptionFinder.find_episodes_by_season(season, self._logger)

        context = {
            "season": season,
            "specialized_table": s.SPECIALIZED_TABLE,
            "episodes": episodes,
        }

        if await self.__check_easter_eggs(context):
            return

        if not episodes:
            await self._responder.send_text(
                await self.get_response(RK.NO_EPISODES_FOUND, args=[str(season)]),
            )
            await self._log_system_message(logging.INFO, get_log_no_episodes_found_message(season))
            return

        if return_json:
            await self._responder.send_json({
                "season": season,
                "episodes": episodes,
                "season_info": season_info,
            })
        else:
            response_parts = self.__split_message(
                format_episode_list_response(season, episodes, season_info),
            )
            for part in response_parts:
                await self._responder.send_text(part)

        await self._log_system_message(
            logging.INFO,
            get_log_episode_list_sent_message(season, self._message.get_username()),
        )


    async def __handle_ranczo_season_11(self) -> None:
        image_path = Path("Ranczo_Sezon11.png")
        with image_path.open("rb") as f:
            image_bytes = f.read()
        await self._responder.send_photo(image_bytes, image_path, get_season_11_petition_message())

    @staticmethod
    def __is_ranczo_season_11(context: dict) -> bool:
        return context["season"] == 11 and context["specialized_table"] == "ranczo_messages"

    def __get_easter_eggs(self) -> List[Tuple[isSeasonCustomFn, Callable[[], Awaitable[None]]]]:
        return [
            (self.__is_ranczo_season_11, self.__handle_ranczo_season_11),
        ]

    async def __check_easter_eggs(self, context: dict) -> bool:
        for predicate, callback in self.__get_easter_eggs():
            if predicate(context):
                await callback()
                return True
        return False

    @staticmethod
    def __split_message(message: str, max_length: int = 4096) -> List[str]:
        parts = []
        while len(message) > max_length:
            split_at = message.rfind("\n", 0, max_length)
            if split_at == -1:
                split_at = max_length
            parts.append(message[:split_at])
            message = message[split_at:].lstrip()
        parts.append(message)
        return parts
