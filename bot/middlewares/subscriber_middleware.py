from bot.database import db
from bot.interfaces.message import AbstractMessage
from bot.middlewares.bot_middleware import BotMiddleware


class SubscriberMiddleware(BotMiddleware):
    async def check(self, message: AbstractMessage) -> bool:
        return await db.is_user_subscribed(message.get_user_id())
