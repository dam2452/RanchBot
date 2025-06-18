from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
)

from aiogram import BaseMiddleware
from aiogram.types import (
    Message,
    TelegramObject,
)

from bot.adapters.telegram.telegram_message import TelegramMessage
from bot.adapters.telegram.telegram_responder import TelegramResponder


class AiogramMiddlewareAdapter(BaseMiddleware):
    def __init__(self, wrapped):
        self._wrapped = wrapped

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        abstract_message = TelegramMessage(event)
        abstract_responder = TelegramResponder(event)

        async def invoke():
            return await handler(event, data)

        return await self._wrapped.handle(abstract_message, abstract_responder, invoke)
