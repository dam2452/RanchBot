from bot.interfaces.message import AbstractMessage


class SignalMessage(AbstractMessage):
    def __init__(self, source: str, text: str, user_id: int) -> None:
        self._source = source
        self._text = text
        self._user_id = user_id

    def get_user_id(self) -> int:
        return self._user_id

    def get_username(self) -> str:
        return self._source

    def get_text(self) -> str:
        return self._text

    def get_chat_id(self) -> int:
        return self._user_id

    def get_sender_id(self) -> int:
        return self._user_id

    def get_full_name(self) -> str:
        return self._source

    def should_reply_json(self) -> bool:
        return False
