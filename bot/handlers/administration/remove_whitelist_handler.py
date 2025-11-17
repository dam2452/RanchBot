import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.remove_whitelist_handler_responses import (
    get_log_user_not_in_whitelist_message,
    get_log_user_removed_message,
)


class RemoveWhitelistHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["removewhitelist", "rmw"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_user_id_digit,
            self.__check_user_exists,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message,
            1,
            await self.get_response(RK.NO_USER_ID_PROVIDED),
        )

    async def __check_user_id_digit(self) -> bool:
        content = self._message.get_text().split()
        if not content[1].isdigit():
            await self.reply_error(RK.NO_USER_ID_PROVIDED)
            return False
        return True

    async def __check_user_exists(self) -> bool:
        user_id = int(self._message.get_text().split()[1])
        user_exists = await DatabaseManager.is_user_in_db(user_id)
        if not user_exists:
            await self.__reply_user_not_found(str(user_id))
            return False
        return True

    async def _do_handle(self) -> None:
        user_id = int(self._message.get_text().split()[1])

        await DatabaseManager.remove_user(user_id)
        await self.__reply_user_removed(user_id)

    async def __reply_user_removed(self, user_id: int) -> None:
        await self.reply(RK.USER_REMOVED, args=[str(user_id)])
        await self._log_system_message(
            logging.INFO,
            get_log_user_removed_message(str(user_id), self._message.get_username()),
        )

    async def __reply_user_not_found(self, user_id: str) -> None:
        await self.reply_error(RK.USER_NOT_IN_WHITELIST, args=[user_id])
        await self._log_system_message(
            logging.WARNING,
            get_log_user_not_in_whitelist_message(int(user_id)),
        )
