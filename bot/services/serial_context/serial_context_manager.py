import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.services.reindex.series_scanner import SeriesScanner


class SerialContextManager:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.scanner = SeriesScanner(logger)

    async def get_user_active_series(self, user_id: int) -> str:
        series = await DatabaseManager.get_user_active_series(user_id)
        return series if series else "ranczo"

    async def set_user_active_series(self, user_id: int, series_name: str) -> None:
        await DatabaseManager.set_user_active_series(user_id, series_name)
        self.logger.info(f"Set active series for user {user_id}: {series_name}")

    async def list_available_series(self) -> List[str]:
        return self.scanner.scan_all_series()
