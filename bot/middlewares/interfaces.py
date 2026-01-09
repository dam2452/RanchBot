from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Awaitable,
    Callable,
)

from bot.interfaces.message import AbstractMessage
from bot.interfaces.responder import AbstractResponder


class AbstractMiddleware(ABC):
    @abstractmethod
    async def handle(
        self,
        message: AbstractMessage,
        responder: AbstractResponder,
        handler: Callable[[], Awaitable[None]],
    ) -> Awaitable[None]:
        pass
