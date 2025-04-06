import asyncio
from enum import Enum
import logging
from logging import LogRecord
import os
from typing import Optional

from aiogram import Bot

from bot.database.database_manager import DatabaseManager
from bot.platforms.rest_runner import run_rest_api
from bot.platforms.telegram_runner import run_telegram_bot
from bot.settings import settings as s
from bot.utils.log import get_log_level


class Platform(Enum):
    TELEGRAM = "telegram"
    REST = "rest"


class DBLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def emit(self, record: LogRecord) -> None:
        if self.loop is not None:
            self.loop.create_task(self.log_to_db(record))

    async def log_to_db(self, record: LogRecord) -> None:
        log_message = self.format(record)
        await DatabaseManager.log_system_message(record.levelname, log_message)


logging.basicConfig(level=get_log_level())
logger = logging.getLogger(__name__)
db_log_handler = DBLogHandler()

try:
    db_log_handler.loop = asyncio.get_running_loop()
except RuntimeError:
    db_log_handler.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(db_log_handler.loop)

logging.getLogger().addHandler(db_log_handler)


async def initialize_common():
    await DatabaseManager.init_pool(
        host=s.POSTGRES_HOST,
        port=s.POSTGRES_PORT,
        database=s.POSTGRES_DB,
        user=s.POSTGRES_USER,
        password=s.POSTGRES_PASSWORD,
        schema=s.POSTGRES_SCHEMA,
    )
    await DatabaseManager.init_db()

    admin_user_id = int(os.getenv("DEFAULT_ADMIN"))
    bot = Bot(token=s.TELEGRAM_BOT_TOKEN)
    user_data = await bot.get_chat(admin_user_id)
    await DatabaseManager.set_default_admin(
        user_id=admin_user_id,
        username=user_data.username or "unknown",
        full_name=user_data.full_name or "Unknown User",
    )
    logger.info("📦 Database initialized and default admin set. 📦")


async def main():
    await initialize_common()

    platform_runners = {
        Platform.TELEGRAM: run_telegram_bot,
        Platform.REST: run_rest_api,
    }

    try:
        runner = platform_runners[Platform(s.PLATFORM)]
    except KeyError:
        raise ValueError(f"Unsupported platform: {s.PLATFORM}")

    await runner()



if __name__ == "__main__":
    asyncio.run(main())
