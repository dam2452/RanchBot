from typing import (
    Awaitable,
    Callable,
    Protocol,
    runtime_checkable,
)

from aiogram import Bot
from aiogram.types import InlineQuery


@runtime_checkable
class SupportsInlineQuery(Protocol):
    def get_inline_handler(self, bot: Bot) -> Callable[[InlineQuery], Awaitable[None]]:
        ...
