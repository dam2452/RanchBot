import logging
from typing import Any, Callable

from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from bot.services.serial_context.serial_context_manager import SerialContextManager


class SerialContextMiddleware(BaseMiddleware):
    def __init__(self, logger: logging.Logger):
        super().__init__()
        self.logger = logger
        self.serial_manager = SerialContextManager(logger)

    async def __call__(
        self,
        handler: Callable,
        event: types.Message,
        data: dict
    ) -> Any:
        user_id = event.from_user.id

        active_series = await self.serial_manager.get_user_active_series(user_id)

        data["active_series"] = active_series

        self.logger.debug(f"User {user_id} active series: {active_series}")

        return await handler(event, data)
