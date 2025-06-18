from abc import (
    ABC,
    abstractmethod,
)
import logging
from typing import (
    Awaitable,
    Callable,
    List,
)

from bot.database.database_manager import DatabaseManager
from bot.database.response_keys import ResponseKey as RK
from bot.interfaces.message import AbstractMessage
from bot.interfaces.responder import AbstractResponder
from bot.responses.bot_message_handler_responses import get_response
from bot.settings import settings


class BotMiddleware(ABC):
    def __init__(self, logger: logging.Logger, supported_commands: List[str]):
        self._logger = logger
        self._supported_commands = supported_commands
        self._logger.info(f"({self.__class__.__name__}) Supported commands: {self._supported_commands}")

    async def handle(
        self,
        message: AbstractMessage,
        responder: AbstractResponder,
        handler: Callable[[], Awaitable[None]],
    ) -> None:
        command = message.get_text().split()[0].lstrip('/')
        if command in self._supported_commands:
            if await self.check_command_limits_and_privileges(message, responder) and await self.check(message):
                await handler()
            else:
                await responder.send_text("❌ Brak uprawnień. ❌")
                self._logger.warning(f"[{self.__class__.__name__}] Unauthorized user: {message.get_user_id()} | Command: {command}")
        else:
            await handler()

    @abstractmethod
    async def check(self, message: AbstractMessage) -> bool:
        pass

    @staticmethod
    async def check_command_limits_and_privileges(message: AbstractMessage, responder: AbstractResponder) -> bool:
        user_id = message.get_user_id()
        is_admin_or_moderator = await DatabaseManager.is_admin_or_moderator(user_id)

        if not is_admin_or_moderator:
            limited = await DatabaseManager.is_command_limited(user_id, settings.MESSAGE_LIMIT, settings.LIMIT_DURATION)
            if limited:
                text = await get_response(RK.LIMIT_EXCEEDED, "BotMessageHandler")
                await responder.send_text(text)
                return False

        return True

    @staticmethod
    async def _does_user_have_moderator_privileges(user_id: int) -> bool:
        return await DatabaseManager.is_user_moderator(user_id) or await DatabaseManager.is_user_admin(user_id)

    @staticmethod
    async def _does_user_have_admin_privileges(user_id: int) -> bool:
        return await DatabaseManager.is_user_admin(user_id)
