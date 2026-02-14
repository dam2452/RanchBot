import logging
from typing import List

from bot.database import db
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.delete_clip_handler_responses import (
    get_clip_deleted_message,
    get_clip_id_not_exist_message,
    get_clip_not_exist_message,
    get_invalid_args_count_message,
    get_log_clip_deleted_message,
    get_log_clip_not_exist_message,
    get_log_no_saved_clips_message,
    get_no_saved_clips_message,
)


class DeleteClipHandler(BotMessageHandler):

    def get_commands(self) -> List[str]:
        return ["usunklip", "deleteclip", "uk"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_clip_exists,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, get_invalid_args_count_message())

    async def __check_clip_exists(self) -> bool:
        content = self._message.get_text().split(maxsplit=1)

        clip_identifier = content[1]
        user_id = self._message.get_user_id()
        user_clips = await db.get_saved_clips(user_id)

        if not user_clips:
            await self.__reply_no_saved_clips()
            return False

        if clip_identifier.isdigit():
            clip_number = int(clip_identifier)
            if clip_number not in range(1, len(user_clips) + 1):
                await self.__reply_clip_index_not_exist(clip_number)
                return False
            return True
        clip_exists = await db.get_clip_by_name(user_id, clip_identifier)
        if not clip_exists:
            await self.__reply_clip_name_not_found(clip_identifier)
            return False
        return True

    async def _do_handle(self) -> None:
        clip_identifier = self._message.get_text().split(maxsplit=1)[1]
        user_id = self._message.get_user_id()
        clip_name_to_delete: str

        if clip_identifier.isdigit():
            clip_number = int(clip_identifier)
            user_clips = await db.get_saved_clips(user_id)
            clip_name_to_delete = user_clips[clip_number - 1].name
        else:
            clip_name_to_delete = clip_identifier

        await db.delete_clip(user_id, clip_name_to_delete)
        await self.__reply_clip_deleted(clip_name_to_delete)

    async def __reply_clip_index_not_exist(self, clip_number: int) -> None:
        await self._reply_error(get_clip_id_not_exist_message(clip_number))
        await self._log_system_message(
            logging.INFO,
            get_log_clip_not_exist_message(clip_number, self._message.get_username()),
        )

    async def __reply_clip_name_not_found(self, clip_name: str) -> None:
        await self._reply_error(get_clip_not_exist_message(clip_name))
        await self._log_system_message(
            logging.INFO,
            get_clip_not_exist_message(clip_name),
        )

    async def __reply_clip_deleted(self, clip_name: str) -> None:
        await self._reply(get_clip_deleted_message(clip_name))
        await self._log_system_message(
            logging.INFO,
            get_log_clip_deleted_message(clip_name, self._message.get_username()),
        )

    async def __reply_no_saved_clips(self) -> None:
        await self._reply_error(get_no_saved_clips_message())
        await self._log_system_message(logging.INFO, get_log_no_saved_clips_message(self._message.get_username()))
