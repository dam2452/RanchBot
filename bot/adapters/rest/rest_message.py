import json

from bot.adapters.rest.models import TextCompatibleCommandWrapper
from bot.interfaces.message import AbstractMessage


class RestMessage(AbstractMessage):
    def __init__(self, payload: TextCompatibleCommandWrapper, user_data: json):
        self.__payload = payload
        self.__user_data = user_data

    def get_user_id(self) -> int:
        return self.__user_data["user_id"]

    def get_username(self) -> str:
        return self.__user_data["username"]

    def get_full_name(self) -> str:
        return self.__user_data["full_name"]

    def get_text(self) -> str:
        return self.__payload.text

    def get_chat_id(self) -> int:
        return self.get_user_id()

    def get_sender_id(self) -> int:
        return self.get_user_id()

    def should_reply_json(self) -> bool:
        return self.__payload.reply_json
