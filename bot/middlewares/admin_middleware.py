from bot.interfaces.message import AbstractMessage
from bot.middlewares.bot_middleware import BotMiddleware


class AdminMiddleware(BotMiddleware):
    async def check(self, message: AbstractMessage) -> bool:
        return await self._does_user_have_admin_privileges(message.get_user_id())
