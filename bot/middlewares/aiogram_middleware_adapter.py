from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
)

from aiogram import BaseMiddleware
from aiogram.types import (
    InlineQuery,
    Message,
    TelegramObject,
)

from bot.adapters.telegram.telegram_inline_query import TelegramInlineQuery
from bot.adapters.telegram.telegram_inline_responder import TelegramInlineResponder
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
        if isinstance(event, Message):
            abstract_message = TelegramMessage(event)
            abstract_responder = TelegramResponder(event)
        elif isinstance(event, InlineQuery):
            abstract_message = TelegramInlineQuery(event)
            abstract_responder = TelegramInlineResponder(event)
        else:
            return await handler(event, data)

        async def invoke():
            return await handler(event, data)

        return await self._wrapped.handle(abstract_message, abstract_responder, invoke)
