import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.services.reindex.series_scanner import SeriesScanner


class SerialContextManager:
    def __init__(self, logger: logging.Logger):
        self.__logger = logger
        self.__scanner = SeriesScanner(logger)

    async def get_user_active_series(self, user_id: int) -> str:
        series_id = await DatabaseManager.get_user_active_series(user_id)
        if series_id:
            series_name = await DatabaseManager.get_series_by_id(series_id)
            return series_name or "ranczo"
        return "ranczo"

    async def set_user_active_series(self, user_id: int, series_name: str) -> None:
        series_id = await DatabaseManager.get_or_create_series(series_name)
        await DatabaseManager.set_user_active_series(user_id, series_id)
        self.__logger.info(f"Set active series for user {user_id}: {series_name}")

    async def list_available_series(self) -> List[str]:
        return self.__scanner.scan_all_series()
