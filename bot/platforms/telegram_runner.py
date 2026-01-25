import logging

from aiogram import (
    Bot,
    Dispatcher,
)
from aiogram.fsm.storage.memory import MemoryStorage

from bot.factory import create_all_factories
from bot.settings import settings

logger = logging.getLogger(__name__)

async def run_telegram_bot():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN.get_secret_value())
    dp = Dispatcher(storage=MemoryStorage())

    factories = create_all_factories(logger, bot)
    for factory in factories:
        factory.create_and_register(dp)

    logger.info("Handlers and middlewares registered successfully.")
    logger.info("🚀 Telegram bot started successfully.")

    await dp.start_polling(bot)
