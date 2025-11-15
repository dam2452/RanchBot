import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.update_user_note_handler_responses import (
    get_log_invalid_user_id_message,
    get_log_note_updated_message,
)


class UpdateUserNoteHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["note"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_user_id,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message, 2, await self.get_response(RK.NO_NOTE_PROVIDED),
        )

    async def __check_user_id(self) -> bool:
        user_id_str = self._message.get_text().split(maxsplit=2)[1]
        if not user_id_str.isdigit():
            await self.__reply_invalid_user_id(user_id_str)
            return False
        return True

    async def _do_handle(self) -> None:
        parts = self._message.get_text().split(maxsplit=2)
        user_id = int(parts[1])
        note = parts[2]
        await self.__update_user_note(user_id, note)

    async def __reply_invalid_user_id(self, user_id_str: str) -> None:
        await self.reply_error(RK.INVALID_USER_ID, args=[user_id_str])
        await self._log_system_message(
            logging.INFO,
            get_log_invalid_user_id_message(self._message.get_username(), user_id_str),
        )

    async def __update_user_note(self, user_id: int, note: str) -> None:
        await DatabaseManager.update_user_note(user_id, note)
        await self.reply(RK.NOTE_UPDATED)
        await self._log_system_message(
            logging.INFO,
            get_log_note_updated_message(self._message.get_username(), user_id, note),
        )
