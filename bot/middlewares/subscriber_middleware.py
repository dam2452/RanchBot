from bot.database.database_manager import DatabaseManager
from bot.interfaces.message import AbstractMessage
from bot.middlewares.bot_middleware import BotMiddleware


class SubscriberMiddleware(BotMiddleware):
    async def check(self, message: AbstractMessage) -> bool:
        return await DatabaseManager.is_user_subscribed(message.get_user_id())
