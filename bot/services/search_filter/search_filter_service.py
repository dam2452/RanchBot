import json
from typing import (
    List,
    Optional,
    Tuple,
)

from bot.database.database_manager import DatabaseManager
from bot.types import SearchFilter


class SearchFilterService:
    @staticmethod
    async def get_active_filters(chat_id: int) -> Optional[SearchFilter]:
        return await DatabaseManager.get_and_touch_user_filters(chat_id)

    @staticmethod
    async def get_active_filters_with_expiry(chat_id: int) -> Tuple[Optional[SearchFilter], bool]:
        active = await DatabaseManager.get_and_touch_user_filters(chat_id)
        if active is not None:
            return active, False
        stored = await DatabaseManager.get_user_filters(chat_id)
        expired = stored is not None and bool(stored.get("filters"))
        return None, expired

    @staticmethod
    async def update_filters(chat_id: int, filter_update: SearchFilter) -> None:
        await DatabaseManager.upsert_user_filters(chat_id, json.dumps(filter_update))

    @staticmethod
    async def reset_filters(chat_id: int) -> None:
        await DatabaseManager.reset_user_filters(chat_id)

    @staticmethod
    async def get_seasons_from_active_filters(chat_id: int) -> Optional[List[int]]:
        search_filter = await SearchFilterService.get_active_filters(chat_id)
        return search_filter.get("seasons") if search_filter else None

    @staticmethod
    async def get_filters_for_display(chat_id: int) -> Optional[SearchFilter]:
        raw = await DatabaseManager.get_user_filters(chat_id)
        if raw is None:
            return None
        return raw["filters"] if raw["filters"] else None
