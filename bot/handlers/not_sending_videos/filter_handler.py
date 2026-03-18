import logging
from typing import List

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.filter_handler_responses import (
    get_filter_info_message,
    get_filter_parse_errors_message,
    get_filter_reset_message,
    get_filter_set_message,
    get_log_filter_reset_message,
    get_log_filter_set_message,
    get_no_args_message,
)
from bot.services.search_filter import (
    FilterParser,
    SearchFilterService,
)


class FilterHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["filtr", "filter", "f"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return []

    def _get_usage_message(self) -> str:
        return get_no_args_message()

    async def _do_handle(self) -> None:
        args = self._message.get_text().split(maxsplit=1)
        subcommand = args[1].strip() if len(args) > 1 else ""

        if not subcommand:
            await self._reply(get_no_args_message())
            return

        chat_id = self._message.get_chat_id()

        if subcommand.lower() == "reset":
            await self.__handle_reset(chat_id)
        elif subcommand.lower() == "info":
            await self.__handle_info(chat_id)
        else:
            await self.__handle_set(chat_id, subcommand)

    async def __handle_reset(self, chat_id: int) -> None:
        await SearchFilterService.reset_filters(chat_id)
        await self._reply(get_filter_reset_message())
        await self._log_system_message(logging.INFO, get_log_filter_reset_message(chat_id))

    async def __handle_info(self, chat_id: int) -> None:
        search_filter = await SearchFilterService.get_filters_for_display(chat_id)
        await self._reply(get_filter_info_message(search_filter))

    async def __handle_set(self, chat_id: int, raw: str) -> None:
        search_filter, errors = FilterParser.parse(raw)
        if errors:
            await self._reply_error(get_filter_parse_errors_message(errors))
            return
        if not search_filter:
            await self._reply(get_no_args_message())
            return
        await SearchFilterService.update_filters(chat_id, search_filter)
        active = await SearchFilterService.get_filters_for_display(chat_id)
        await self._reply(get_filter_set_message(active or search_filter))
        await self._log_system_message(logging.INFO, get_log_filter_set_message(chat_id))
