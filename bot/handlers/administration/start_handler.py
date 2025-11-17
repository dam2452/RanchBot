import logging
from typing import (
    Dict,
    List,
)

from bot.database.response_keys import ResponseKey as RK
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.administration.start_handler_responses import (
    get_log_received_start_command,
    get_log_start_message_sent,
)
from bot.utils.functions import remove_diacritics_and_lowercase


class StartHandler(BotMessageHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__RESPONSES: Dict[str, str] = {
            "lista": RK.LIST_MESSAGE,
            "list": RK.LIST_MESSAGE,
            "l": RK.LIST_MESSAGE,

            "wszystko": RK.ALL_MESSAGE,
            "all": RK.ALL_MESSAGE,
            "a": RK.ALL_MESSAGE,

            "wyszukiwanie": RK.SEARCH_MESSAGE,
            "search": RK.SEARCH_MESSAGE,
            "s": RK.SEARCH_MESSAGE,

            "edycja": RK.EDIT_MESSAGE,
            "edit": RK.EDIT_MESSAGE,
            "e": RK.EDIT_MESSAGE,

            "zarzadzanie": RK.MANAGEMENT_MESSAGE,
            "management": RK.MANAGEMENT_MESSAGE,
            "m": RK.MANAGEMENT_MESSAGE,

            "raportowanie": RK.REPORTING_MESSAGE,
            "reporting": RK.REPORTING_MESSAGE,
            "r": RK.REPORTING_MESSAGE,

            "subskrypcje": RK.SUBSCRIPTIONS_MESSAGE,
            "subscriptions": RK.SUBSCRIPTIONS_MESSAGE,
            "sub": RK.SUBSCRIPTIONS_MESSAGE,

            "skroty": RK.SHORTCUTS_MESSAGE,
            "shortcuts": RK.SHORTCUTS_MESSAGE,
            "sh": RK.SHORTCUTS_MESSAGE,
        }

    def get_commands(self) -> List[str]:
        return ["start", "s", "help", "h", "pomoc"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message,
            0,
            await self.get_response(RK.INVALID_COMMAND_MESSAGE),
            1
        )

    async def _do_handle(self) -> None:
        content = self._message.get_text().split()
        await self._log_system_message(
            logging.INFO,
            get_log_received_start_command(self._message.get_username(), self._message.get_text()),
        )

        if len(content) == 1:
            await self.__send_message(await self.get_response(RK.BASIC_MESSAGE))
        else:
            command = remove_diacritics_and_lowercase(content[1])
            response_key = self.__RESPONSES.get(command, RK.INVALID_COMMAND_MESSAGE)
            await self.__send_message(await self.get_response(response_key))

    async def __send_message(self, text: str) -> None:
        await self._responder.send_markdown(text)
        await self._log_system_message(
            logging.INFO,
            get_log_start_message_sent(self._message.get_username()),
        )
