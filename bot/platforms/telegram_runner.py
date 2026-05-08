import logging

from aiogram import (
    Bot,
    Dispatcher,
)
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from bot.factory import create_all_factories
from bot.platforms.telegram_registrar import TelegramRegistrar
from bot.settings import settings

logger = logging.getLogger(__name__)


class OptimizedAiohttpSession(AiohttpSession):
    def __init__(self, **kwargs):
        super().__init__(limit=200, **kwargs)
        self._connector_init.update({
            "limit_per_host": 50,
            "ttl_dns_cache": 300,
        })


async def run_telegram_bot() -> None:
    session = OptimizedAiohttpSession()
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN.get_secret_value(),
        session=session,
    )
    dp = Dispatcher(storage=MemoryStorage())

    factories = create_all_factories(logger)
    TelegramRegistrar(factories, dp, bot).register()

    logger.info("Handlers and middlewares registered successfully.")
    logger.info("Telegram bot started successfully.")

    await dp.start_polling(bot)
