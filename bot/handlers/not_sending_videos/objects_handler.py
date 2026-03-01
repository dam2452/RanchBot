import logging
import math
import re
from typing import (
    List,
    Optional,
)

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.objects_handler_responses import (
    format_object_scenes,
    format_objects_list,
    get_invalid_quantity_filter_message,
    get_log_object_scenes_message,
    get_log_objects_list_message,
    get_no_objects_message,
)
from bot.search.object_finder import ObjectFinder
from bot.types import QuantityFilter

_QUANTITY_FILTER_PATTERN = re.compile(r"^(>=|<=|>|<|=)?(\d+)$")


class ObjectsHandler(BotMessageHandler):
    def get_commands(self) -> List[str]:
        return ["obiekt", "object", "obj"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_invalid_quantity_filter_message("")

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(self._message, 0, math.inf)

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()[1:]
        user_id = self._message.get_user_id()
        series_name = await self._get_user_active_series(user_id)

        if not args:
            await self.__handle_list_mode(series_name)
        elif len(args) == 1:
            await self.__handle_object_mode(args[0], series_name)
        else:
            await self.__handle_object_filter_mode(args[0], args[1], series_name)

    async def __handle_list_mode(self, series_name: str) -> None:
        objects = await ObjectFinder.get_all_objects(series_name=series_name, logger=self._logger)
        if not objects:
            await self._reply_error(get_no_objects_message())
            return
        await self._reply(format_objects_list(objects))
        await self._log_system_message(
            logging.INFO,
            get_log_objects_list_message(len(objects), self._message.get_username()),
        )

    async def __handle_object_mode(self, class_name: str, series_name: str) -> None:
        scenes = await ObjectFinder.get_scenes_by_object(
            class_name=class_name.lower(),
            series_name=series_name,
            logger=self._logger,
        )
        await self._reply(format_object_scenes(class_name, scenes))
        await self._log_system_message(
            logging.INFO,
            get_log_object_scenes_message(class_name, len(scenes), self._message.get_username()),
        )

    async def __handle_object_filter_mode(
        self,
        class_name: str,
        qty_raw: str,
        series_name: str,
    ) -> None:
        qty_filter = ObjectsHandler.__parse_quantity_filter(qty_raw)
        if qty_filter is None:
            await self._reply_error(get_invalid_quantity_filter_message(qty_raw))
            return
        scenes = await ObjectFinder.get_scenes_by_object(
            class_name=class_name.lower(),
            series_name=series_name,
            logger=self._logger,
        )
        filtered = ObjectFinder.apply_quantity_filter(scenes, qty_filter)
        await self._reply(format_object_scenes(class_name, filtered, qty_filter_str=qty_raw))
        await self._log_system_message(
            logging.INFO,
            get_log_object_scenes_message(class_name, len(filtered), self._message.get_username()),
        )

    @staticmethod
    def __parse_quantity_filter(raw: str) -> Optional[QuantityFilter]:
        match = _QUANTITY_FILTER_PATTERN.match(raw.strip())
        if not match:
            return None
        operator = match.group(1) or "="
        value = int(match.group(2))
        return QuantityFilter(operator=operator, value=value)
