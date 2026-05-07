import logging
import math
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.filter_handler_responses import (
    get_filter_help_message,
    get_filter_help_schema_json,
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
    FilterValidator,
)


class FilterHandler(BotMessageHandler):
    __parser = FilterParser()

    def get_commands(self) -> List[str]:
        return ["filtr", "filter", "f"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_no_args_message()

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 1, math.inf)

    async def _do_handle(self) -> None:
        args = self._message.get_text().split(maxsplit=1)
        subcommand = args[1].strip()
        chat_id = self._message.get_chat_id()

        sub = subcommand.lower()
        if sub == "reset":
            await self.__handle_reset(chat_id)
        elif sub == "info":
            await self.__handle_info(chat_id)
        elif sub in {"help", "pomoc", "?"}:
            await self.__handle_help()
        else:
            series_name = await self._get_user_active_series(self._message.get_user_id())
            await self.__handle_set(chat_id, subcommand, series_name)

    async def __handle_reset(self, chat_id: int) -> None:
        await DatabaseManager.reset_user_filters(chat_id)
        await self._reply(get_filter_reset_message(), data={"filter": None})
        await self._log_system_message(logging.INFO, get_log_filter_reset_message(chat_id))

    async def __handle_info(self, chat_id: int) -> None:
        search_filter = await DatabaseManager.get_user_filters(chat_id)
        await self._reply(
            get_filter_info_message(search_filter),
            data={"filter": search_filter},
        )

    async def __handle_help(self) -> None:
        await self._reply(
            get_filter_help_message(),
            data={"schema": get_filter_help_schema_json()},
        )

    async def __handle_set(self, chat_id: int, raw: str, series_name: str) -> None:
        search_filter, errors = self.__parser.parse(raw)
        if errors:
            await self._reply_error(
                get_filter_parse_errors_message(errors),
                data={"errors": errors},
            )
            return
        if not search_filter:
            await self._reply(get_no_args_message(), data={"filter": None, "notes": []})
            return
        resolved_filter, notes = await FilterValidator.resolve(search_filter, series_name, self._logger)
        await DatabaseManager.upsert_user_filters(chat_id, resolved_filter)
        active = await DatabaseManager.get_user_filters(chat_id)
        final_filter = active or resolved_filter
        await self._reply(
            get_filter_set_message(final_filter, notes),
            data={"filter": final_filter, "notes": notes},
        )
        await self._log_system_message(logging.INFO, get_log_filter_set_message(chat_id))
