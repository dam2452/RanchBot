import logging
import os
from typing import (
    Dict,
    Protocol,
)

from bot.database.database_manager import DatabaseManager

LOG_LEVELS: Dict[int, str] = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}

class Logger(Protocol):
    def log(self, level: int, message: str) -> None:
        ...

    def info(self, message: str) -> None:
        ...

    def error(self, message: str) -> None:
        ...


async def log_system_message(level: int, message: str, logger: Logger) -> None:
    logger.log(level, message)
    await DatabaseManager.log_system_message(LOG_LEVELS[level], message)


async def log_user_activity(user_id: int, message: str, logger: Logger) -> None:
    await log_system_message(logging.INFO, message, logger)
    await DatabaseManager.log_user_activity(user_id, message)

def get_log_level(env_var: str = "LOG_LEVEL", default: str = "INFO") -> int:
    log_level_str = os.getenv(env_var, default).upper()
    return getattr(logging, log_level_str)
