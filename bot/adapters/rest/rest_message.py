import json

from bot.adapters.rest.models import CommandRequest
from bot.interfaces.message import AbstractMessage


class RestMessage(AbstractMessage):
    def __init__(self, payload: CommandRequest, user_data: json):
        payload.json = True
        self._payload = payload
        self._user_data = user_data

    def get_user_id(self) -> int:
        return self._user_data["user_id"]

    def get_username(self) -> str:
        return self._user_data["username"]

    def get_full_name(self) -> str:
        return self._user_data["full_name"]

    def get_text(self) -> str:
        return self._payload.text

    def get_chat_id(self) -> int:
        return self.get_user_id()

    def get_sender_id(self) -> int:
        return self.get_user_id()

    def get_json_flag(self) -> bool:
        return self._payload.json
