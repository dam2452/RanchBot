import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.services.reindex.series_scanner import SeriesScanner
from bot.settings import settings


class SerialContextManager:
    def __init__(self, logger: logging.Logger):
        self.__logger = logger
        self.__scanner = SeriesScanner(logger)

    @staticmethod
    async def get_user_active_series(user_id: int) -> str:
        series_names = await SerialContextManager.get_user_active_series_list(user_id)
        return series_names[0] if series_names else settings.DEFAULT_SERIES

    @staticmethod
    async def get_user_active_series_list(user_id: int) -> List[str]:
        return await DatabaseManager.get_user_active_series_names(user_id)

    async def set_user_active_series(self, user_id: int, series_name: str) -> None:
        await self.set_user_active_series_list(user_id, [series_name])

    async def set_user_active_series_list(self, user_id: int, series_names: List[str]) -> None:
        if not series_names:
            await DatabaseManager.set_user_active_series_names(user_id, [])
            self.__logger.info(f"Set active series for user {user_id}: all")
            return
        for name in series_names:
            await DatabaseManager.get_or_create_series(name)
        await DatabaseManager.set_user_active_series_names(user_id, series_names)
        self.__logger.info(f"Set active series for user {user_id}: {series_names}")

    async def list_available_series(self) -> List[str]:
        return self.__scanner.scan_all_series()
