import asyncio
from dataclasses import dataclass
import logging
from logging import LogRecord
import os
from typing import (
    Awaitable,
    Callable,
    Optional,
    Tuple,
)

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from bot.database import db
from bot.platforms.rest_runner import run_rest_api
from bot.platforms.telegram_runner import run_telegram_bot
from bot.settings import settings as s
from bot.utils.log import get_log_level


@dataclass(frozen=True)
class PlatformConfig:
    name: str
    enabled: Callable[[], bool]
    runner: Callable[[], Awaitable[None]]


class DBLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def emit(self, record: LogRecord) -> None:
        if self.loop is not None:
            self.loop.create_task(self.log_to_db(record))

    async def log_to_db(self, record: LogRecord) -> None:
        log_message = self.format(record)
        await db.log_system_message(record.levelname, log_message)


logging.basicConfig(level=get_log_level())
logger = logging.getLogger(__name__)
db_log_handler = DBLogHandler()

try:
    db_log_handler.loop = asyncio.get_running_loop()
except RuntimeError:
    db_log_handler.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(db_log_handler.loop)

logging.getLogger().addHandler(db_log_handler)


async def initialize_common_and_set_admin():
    await db.ensure_db_initialized()
    logger.info("DB initialization process ensured by main application.")

    admin_user_id_str = os.getenv("DEFAULT_ADMIN")
    if not admin_user_id_str:
        logger.error("DEFAULT_ADMIN environment variable is not set. Cannot set default admin.")
        return

    try:
        admin_user_id = int(admin_user_id_str)
    except ValueError:
        logger.error(f"Invalid DEFAULT_ADMIN ID: '{admin_user_id_str}'. Must be an integer.")
        return

    if s.ENABLE_TELEGRAM:
        if not s.TELEGRAM_BOT_TOKEN:
            logger.error(
                "Telegram is enabled but TELEGRAM_BOT_TOKEN is missing. Cannot set default admin from Telegram.",
            )
            return

        bot_instance = None
        try:
            bot_instance = Bot(token=s.TELEGRAM_BOT_TOKEN.get_secret_value())
            user_data = await bot_instance.get_chat(admin_user_id)
            await db.set_default_admin(
                user_id=admin_user_id,
                username=user_data.username or f"tg_user_{admin_user_id}",
                full_name=user_data.full_name or "Telegram Default Admin",
            )
            logger.info("Default admin set using Telegram data.")
        except TelegramAPIError as e_tg:
            logger.error(f"Telegram API error while setting default admin for user ID {admin_user_id}: {e_tg}")
        except Exception as e_other:
            logger.error(f"Unexpected error while setting default admin using Telegram API for user ID {admin_user_id}: {e_other}")
        finally:
            if bot_instance:
                await bot_instance.session.close()
    else:
        logger.info("Telegram platform is disabled. Default admin setup via Telegram API is skipped.")


PLATFORM_REGISTRY: Tuple[PlatformConfig, ...] = (
    PlatformConfig(
        name="Telegram bot",
        enabled=lambda: s.ENABLE_TELEGRAM,
        runner=run_telegram_bot,
    ),
    PlatformConfig(
        name="REST API",
        enabled=lambda: s.ENABLE_REST,
        runner=run_rest_api,
    ),
)


async def main():
    await initialize_common_and_set_admin()

    enabled_platforms = [p for p in PLATFORM_REGISTRY if p.enabled()]
    disabled_platforms = [p for p in PLATFORM_REGISTRY if not p.enabled()]

    for platform in enabled_platforms:
        logger.info(f"Starting {platform.name} platform")

    for platform in disabled_platforms:
        logger.info(f"{platform.name} platform disabled")

    if not enabled_platforms:
        logger.critical("CRITICAL: No platform enabled! Configure at least one platform.")
        return

    logger.info(f"Running {len(enabled_platforms)} platform(s)")
    await asyncio.gather(*[p.runner() for p in enabled_platforms])


if __name__ == "__main__":
    asyncio.run(main())
