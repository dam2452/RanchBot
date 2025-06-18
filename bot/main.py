import asyncio
from enum import Enum
import logging
from logging import LogRecord
import os
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

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


async def initialize_common_and_set_admin():
    await DatabaseManager.ensure_db_initialized()
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

    if s.PLATFORM.lower() == "telegram":
        if not s.TELEGRAM_BOT_TOKEN:
            logger.error(
                "Platform is 'telegram' but TELEGRAM_BOT_TOKEN is missing. Cannot set default admin from Telegram.",
            )
            return

        bot_instance = None
        try:
            bot_instance = Bot(token=s.TELEGRAM_BOT_TOKEN)
            user_data = await bot_instance.get_chat(admin_user_id)
            await DatabaseManager.set_default_admin(
                user_id=admin_user_id,
                username=user_data.username or f"tg_user_{admin_user_id}",
                full_name=user_data.full_name or "Telegram Default Admin",
            )
            logger.info("Default admin set using Telegram data.")
        except TelegramAPIError as e_tg:
            logger.error(f"Telegram API error while setting default admin for user ID {admin_user_id}: {e_tg}")
        except Exception as e_other: # pylint: disable=broad-exception-caught
            logger.error(f"Unexpected error while setting default admin using Telegram API for user ID {admin_user_id}: {e_other}")
        finally:
            if bot_instance:
                await bot_instance.session.close()
    else:
        logger.info(f"Platform is '{s.PLATFORM}'. Default admin setup via Telegram API is skipped.")


async def main():
    await initialize_common_and_set_admin()

    platform_runners = {
        Platform.TELEGRAM: run_telegram_bot,
        Platform.REST: run_rest_api,
    }

    current_platform_enum: Optional[Platform] = None
    try:
        current_platform_enum = Platform(s.PLATFORM.lower())
    except ValueError:
        logger.critical(f"CRITICAL: Unsupported platform string in settings: '{s.PLATFORM}'. Application cannot start.")
        return

    runner = platform_runners.get(current_platform_enum)

    if runner:
        logger.info(f"Starting platform: {current_platform_enum.value}")
        await runner()
    else:
        logger.critical(
            f"CRITICAL: No runner found for platform: '{s.PLATFORM}'. This should not happen if PLATFORM enum value is valid and in platform_runners.",
        )
        raise ValueError(f"No runner configured for platform enum value: {current_platform_enum}")


if __name__ == "__main__":
    asyncio.run(main())
