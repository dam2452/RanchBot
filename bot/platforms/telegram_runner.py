import logging

from aiogram import (
    Bot,
    Dispatcher,
)
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from bot.factory import create_all_factories
from bot.middlewares.serial_context_middleware import SerialContextMiddleware
from bot.settings import settings

logger = logging.getLogger(__name__)


class OptimizedAiohttpSession(AiohttpSession):
    def __init__(self, **kwargs):
        super().__init__(limit=200, **kwargs)
        self._connector_init.update({
            "limit_per_host": 50,
            "ttl_dns_cache": 300,
        })


async def run_telegram_bot():
    session = OptimizedAiohttpSession()
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN.get_secret_value(),
        session=session,
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware.register(SerialContextMiddleware(logger))

    factories = create_all_factories(logger, bot)
    for factory in factories:
        factory.create_and_register(dp)

    inline_handlers = [f.get_inline_handler() for f in factories]
    inline_handlers = [h for h in inline_handlers if h is not None]

    if inline_handlers:
        async def combined_inline_handler(inline_query):
            try:
                for handler in inline_handlers:
                    await handler(inline_query)
                    break
            except Exception as e:
                logger.error(f"Error in combined inline handler: {type(e).__name__}: {e}", exc_info=True)

        dp.inline_query.register(combined_inline_handler)
        logger.info("Combined inline handler registered")

    logger.info("Handlers and middlewares registered successfully.")
    logger.info("🚀 Telegram bot started successfully.")

    await dp.start_polling(bot)
