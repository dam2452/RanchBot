from aiogram.types import InlineQuery

from bot.interfaces.message import AbstractMessage


class TelegramInlineQuery(AbstractMessage):
    def __init__(self, message: InlineQuery) -> None:
        self._message = message

    def get_user_id(self) -> int:
        return self._message.from_user.id

    def get_username(self) -> str:
        return self._message.from_user.username

    def get_text(self) -> str:
        return self._message.query

    def get_chat_id(self) -> int:
        raise RuntimeError("TelegramInlineQuery.get_chat_id should not be called")

    def get_sender_id(self) -> int:
        return self._message.from_user.id

    def get_full_name(self) -> str:
        return self._message.from_user.first_name + " " + self._message.from_user.last_name

    def should_reply_json(self) -> bool:
        return False
