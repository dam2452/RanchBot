from typing import Optional
from uuid import uuid4

from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)


def generate_error_result(title: str, text: Optional[str] = None) -> InlineQueryResultArticle:
    return InlineQueryResultArticle(
        id=str(uuid4()),
        title=title,
        input_message_content=InputTextMessageContent(
            message_text=text or title,
        ),
    )

async def answer_error(title: str, text: str, inline_query: InlineQuery) -> None:
    await inline_query.answer(
        results=[generate_error_result(title, text)],
        cache_time=0,
        is_personal=True,
    )
