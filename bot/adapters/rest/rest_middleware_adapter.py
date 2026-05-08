from typing import (
    Awaitable,
    Callable,
    List,
)

from fastapi import HTTPException

from bot.middlewares.bot_middleware import BotMiddleware


class RestMiddlewareAdapter:
    def __init__(self, middlewares: List[BotMiddleware]) -> None:
        self._middlewares = middlewares

    async def execute(
        self,
        message,
        responder,
        handler: Callable[[], Awaitable[None]],
    ) -> None:
        chain = handler
        for mw in reversed(self._middlewares):
            prev = chain
            chain = self._wrap(mw, message, responder, prev)
        await chain()

    @staticmethod
    def _wrap(
        middleware: BotMiddleware,
        message,
        responder,
        next_handler: Callable[[], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        async def wrapped() -> None:
            original_send_text = responder.send_text
            access_denied = False

            async def tracked_send_text(text: str) -> None:
                nonlocal access_denied
                access_denied = True
                await original_send_text(text)

            responder.send_text = tracked_send_text
            await middleware.handle(message, responder, next_handler)
            responder.send_text = original_send_text

            if access_denied:
                raise HTTPException(status_code=403, detail="Access denied.")

        return wrapped
