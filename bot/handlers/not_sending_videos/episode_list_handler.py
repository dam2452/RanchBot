import logging
from typing import (
    Awaitable,
    Callable,
    List,
)

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.episode_list_handler_responses import (
    format_episode_list_response,
    get_invalid_args_count_message,
    get_log_episode_list_sent_message,
    get_log_no_episodes_found_message,
    get_no_episodes_found_message,
)
from bot.search.transcription_finder import TranscriptionFinder

isSeasonCustomFn = Callable[[dict], bool]
onCustomSeasonFn = Callable[[], Awaitable[None]]


class EpisodeListHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["odcinki", "episodes", "o"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_invalid_args_count_message())

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()

        try:
            season = int(args[1])
        except (IndexError, ValueError):
            return await self.reply_error(get_invalid_args_count_message())

        season_info = await TranscriptionFinder.get_season_details_from_elastic(logger=self._logger)
        episodes = await TranscriptionFinder.find_episodes_by_season(season, self._logger)

        if not episodes:
            return await self.__reply_no_episodes_found(season)

        if self._message.should_reply_json():
            await self._responder.send_json({
                    "season": season,
                    "episodes": episodes,
                    "season_info": season_info,
            })
        else:
            response = format_episode_list_response(season, episodes, season_info)
            for part in self.__split_message(response):
                await self._answer_markdown(part)

        return await self._log_system_message(
            logging.INFO,
            get_log_episode_list_sent_message(season, self._message.get_username()),
        )

    async def __reply_no_episodes_found(self, season: int) -> None:
        await self.reply_error(get_no_episodes_found_message(season))
        await self._log_system_message(logging.INFO, get_log_no_episodes_found_message(season))

    @staticmethod
    def __split_message(full_message: str, max_length: int = 4096) -> List[str]:
        parts = []
        while len(full_message) > max_length:
            split_at = full_message.rfind("\n", 0, max_length)
            if split_at == -1:
                split_at = max_length
            parts.append(full_message[:split_at])
            full_message = full_message[split_at:].lstrip()
        parts.append(full_message)
        return parts
