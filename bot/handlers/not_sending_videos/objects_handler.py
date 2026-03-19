import json
import logging
import math
import re
from typing import (
    List,
    Optional,
)

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.responses.not_sending_videos.objects_handler_responses import (
    format_object_scenes,
    format_object_scenes_full,
    format_objects_list,
    format_objects_list_full,
    get_invalid_quantity_filter_message,
    get_log_object_scenes_message,
    get_log_objects_list_message,
    get_no_objects_message,
    get_object_not_found_message,
    object_scene_to_search_segment,
)
from bot.search.video_frames import ObjectFinder
from bot.services.search_filter import SearchFilterService
from bot.settings import settings as s
from bot.types import (
    ObjectScene,
    QuantityFilter,
)

_QUANTITY_FILTER_PATTERN = re.compile(r"^(>=|<=|>|<|=)?(\d+)$")


class ObjectsHandler(BotMessageHandler):
    __SHORT_COMMANDS: List[str] = ["obiekt", "object", "obj"]
    __FULL_COMMANDS: List[str] = ["objl", "objlista"]
    __SEARCH_COMMANDS: List[str] = ["szukajobiekt", "szo"]

    def get_commands(self) -> List[str]:
        return ObjectsHandler.__SHORT_COMMANDS + ObjectsHandler.__FULL_COMMANDS + ObjectsHandler.__SEARCH_COMMANDS

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [self.__check_argument_count]

    def _get_usage_message(self) -> str:
        return get_invalid_quantity_filter_message("")

    async def __check_argument_count(self) -> bool:
        command = self._message.get_text().split()[0].lstrip("/").lower()
        min_args = 1 if command in ObjectsHandler.__SEARCH_COMMANDS else 0
        return await self._validate_argument_count(self._message, min_args, math.inf)

    async def _do_handle(self) -> None:
        text_parts = self._message.get_text().split()
        command = text_parts[0].lstrip("/").lower()
        args = text_parts[1:]
        is_full = command in ObjectsHandler.__FULL_COMMANDS
        user_id = self._message.get_user_id()
        series_name = await self._get_user_active_series(user_id)

        if not args:
            await self.__handle_list_mode(series_name, is_full)
        else:
            seasons = await SearchFilterService.get_seasons_from_active_filters(self._message.get_chat_id())
            if len(args) == 1:
                await self.__handle_object_mode(args[0], series_name, is_full, seasons)
            else:
                await self.__handle_object_filter_mode(args[0], args[1], series_name, is_full, seasons)

    async def __handle_list_mode(self, series_name: str, is_full: bool) -> None:
        objects = await ObjectFinder.get_all_objects(series_name=series_name, logger=self._logger)
        if not objects:
            await self._reply_error(get_no_objects_message())
            return
        if is_full:
            await self._send_document(
                format_objects_list_full(objects),
                f"{s.BOT_USERNAME}_Obiekty.txt",
                "Pełna lista obiektów",
            )
        else:
            await self._reply(format_objects_list(objects))
        await self._log_system_message(
            logging.INFO,
            get_log_objects_list_message(len(objects), self._message.get_username()),
        )

    async def __handle_object_mode(
        self,
        query: str,
        series_name: str,
        is_full: bool,
        seasons: Optional[List[int]] = None,
    ) -> None:
        class_name = await self.__resolve_object_class(query, series_name)
        if class_name is None:
            return
        scenes = await ObjectFinder.get_scenes_by_object(
            class_name=class_name,
            series_name=series_name,
            logger=self._logger,
            seasons=seasons,
        )
        await self.__save_scenes_to_last_search(scenes, class_name)
        if is_full:
            await self._send_document(
                format_object_scenes_full(class_name, scenes),
                f"{s.BOT_USERNAME}_Sceny_{self._sanitize_filename(class_name)}.txt",
                f"Pełna lista scen: {class_name}",
            )
        else:
            await self._reply(format_object_scenes(class_name, scenes))
        await self._log_system_message(
            logging.INFO,
            get_log_object_scenes_message(class_name, len(scenes), self._message.get_username()),
        )

    async def __handle_object_filter_mode(
        self,
        query: str,
        qty_raw: str,
        series_name: str,
        is_full: bool,
        seasons: Optional[List[int]] = None,
    ) -> None:
        qty_filter = ObjectsHandler.__parse_quantity_filter(qty_raw)
        if qty_filter is None:
            await self._reply_error(get_invalid_quantity_filter_message(qty_raw))
            return
        class_name = await self.__resolve_object_class(query, series_name)
        if class_name is None:
            return
        scenes = await ObjectFinder.get_scenes_by_object(
            class_name=class_name,
            series_name=series_name,
            logger=self._logger,
            seasons=seasons,
        )
        filtered = ObjectFinder.apply_quantity_filter(scenes, qty_filter)
        await self.__save_scenes_to_last_search(filtered, class_name, qty_raw)
        if is_full:
            await self._send_document(
                format_object_scenes_full(class_name, filtered, qty_filter_str=qty_raw),
                f"{s.BOT_USERNAME}_Sceny_{self._sanitize_filename(class_name)}_{qty_raw}.txt",
                f"Pełna lista scen: {class_name} ({qty_raw})",
            )
        else:
            await self._reply(format_object_scenes(class_name, filtered, qty_filter_str=qty_raw))
        await self._log_system_message(
            logging.INFO,
            get_log_object_scenes_message(class_name, len(filtered), self._message.get_username()),
        )

    async def __resolve_object_class(self, query: str, series_name: str) -> Optional[str]:
        class_name = await ObjectFinder.find_best_matching_object(
            query=query,
            series_name=series_name,
            logger=self._logger,
        )
        if class_name is None:
            await self._reply_error(get_object_not_found_message(query))
        return class_name

    async def __save_scenes_to_last_search(
        self,
        scenes: List[ObjectScene],
        class_name: str,
        qty_filter_str: Optional[str] = None,
    ) -> None:
        if not scenes:
            return
        segments = [object_scene_to_search_segment(scene) for scene in scenes]
        quote = f"{class_name} {qty_filter_str}" if qty_filter_str else class_name
        await DatabaseManager.insert_last_search(
            chat_id=self._message.get_chat_id(),
            quote=quote,
            segments=json.dumps(segments),
        )

    @staticmethod
    def __parse_quantity_filter(raw: str) -> Optional[QuantityFilter]:
        match = _QUANTITY_FILTER_PATTERN.match(raw.strip())
        if not match:
            return None
        operator = match.group(1) or "="
        value = int(match.group(2))
        return QuantityFilter(operator=operator, value=value)
