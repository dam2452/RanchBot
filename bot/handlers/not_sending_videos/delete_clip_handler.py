import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.delete_clip_handler_responses import (
    get_log_clip_deleted_message,
    get_log_clip_not_exist_message,
)


class DeleteClipHandler(BotMessageHandler):

    def get_commands(self) -> List[str]:
        return ["usunklip", "deleteclip", "uk"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_clip_number_format,
            self.__check_clip_exists,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message, 2, await self.get_response(RK.INVALID_ARGS_COUNT),
        )

    async def __check_clip_number_format(self) -> bool:
        content = self._message.get_text().split()
        if not content[1].isdigit():
            await self.__reply_invalid_args_count()
            return False
        return True

    async def __check_clip_exists(self) -> bool:
        content = self._message.get_text().split()
        clip_number = int(content[1])
        user_clips = await DatabaseManager.get_saved_clips(self._message.get_user_id())

        if clip_number not in range(1, len(user_clips) + 1):
            await self.__reply_clip_not_exist(clip_number)
            return False
        return True

    async def _do_handle(self) -> None:
        clip_number = int(self._message.get_text().split()[1])

        user_clips = await DatabaseManager.get_saved_clips(self._message.get_user_id())
        clip_to_delete = user_clips[clip_number - 1]
        await DatabaseManager.delete_clip(self._message.get_user_id(), clip_to_delete.name)

        await self.__reply_clip_deleted(clip_to_delete.name)

    async def __reply_invalid_args_count(self) -> None:
        text = await self.get_response(RK.INVALID_ARGS_COUNT)
        await self._answer(text)
        await self._log_system_message(logging.INFO, text)

    async def __reply_clip_not_exist(self, clip_number: int) -> None:
        text = await self.get_response(RK.CLIP_NOT_EXIST, args=[str(clip_number)])
        await self._answer(text)
        await self._log_system_message(
            logging.INFO,
            get_log_clip_not_exist_message(clip_number, self._message.get_username()),
        )

    async def __reply_clip_deleted(self, clip_name: str) -> None:
        text = await self.get_response(RK.CLIP_DELETED, args=[clip_name])
        await self._answer(text)
        await self._log_system_message(
            logging.INFO,
            get_log_clip_deleted_message(clip_name, self._message.get_username()),
        )
