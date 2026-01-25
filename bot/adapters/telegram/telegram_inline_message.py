from aiogram.types import InlineQuery

from bot.interfaces.message import AbstractMessage

# TODO FIXME IMPLEMENT
class TelegramInlineMessage(AbstractMessage):
    def __init__(self, message: InlineQuery):
        self._message = message

    def get_user_id(self) -> int:
        return self._message.from_user.id

    def get_username(self) -> str:
        return self._message.from_user.username or "unknown"

    def get_text(self) -> str:
        return self._message.text or ""

    def get_chat_id(self) -> int:
        return self._message.chat.id

    def get_sender_id(self) -> int:
        return self._message.from_user.id

    def get_full_name(self) -> str:
        return self._message.from_user.full_name or self.get_username()

    def should_reply_json(self) -> bool:
        return False
