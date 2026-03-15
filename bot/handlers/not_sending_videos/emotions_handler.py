import logging
from typing import List

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.emotions_handler_responses import (
    EmotionInfo,
    format_emotions_list,
    get_invalid_args_count_message,
    get_log_emotions_listed_message,
    map_emotion_to_pl,
)
from bot.search.video_frames_finder import CharacterFinder


class EmotionsHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["emocje", "emotion", "e"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_invalid_args_count_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 0)

    async def _do_handle(self) -> None:
        user_id = self._message.get_user_id()
        series_name = await self._get_user_active_series(user_id)

        emotion_labels = await CharacterFinder.get_all_emotions(
            series_name=series_name,
            logger=self._logger,
        )

        emotions = [
            EmotionInfo(label_en=label, label_pl=map_emotion_to_pl(label))
            for label in emotion_labels
        ]
        emotions.sort(key=lambda e: e["label_pl"])

        response = format_emotions_list(emotions)
        await self._reply(response)
        await self._log_system_message(
            logging.INFO,
            get_log_emotions_listed_message(len(emotions), self._message.get_username()),
        )
