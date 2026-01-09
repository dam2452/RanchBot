from bot.interfaces.message import AbstractMessage
from bot.middlewares.bot_middleware import BotMiddleware


class AnyMiddleware(BotMiddleware):
    async def check(self, message: AbstractMessage) -> bool:
        command = message.get_text().split()[0].lstrip('/')
        if command in self._supported_commands:
            self._logger.info(f"[AnyMiddleware] Command '{command}' used by user {message.get_user_id()}")
        return True
