from bot.interfaces.message import AbstractMessage


class SignalMessage(AbstractMessage):
    def __init__(self, source: str, text: str, user_id: int) -> None:
        self.__source = source
        self.__text = text
        self.__user_id = user_id

    def get_user_id(self) -> int:
        return self.__user_id

    def get_username(self) -> str:
        return self.__source

    def get_text(self) -> str:
        return self.__text

    def get_chat_id(self) -> int:
        return self.__user_id

    def get_sender_id(self) -> int:
        return self.__user_id

    def get_full_name(self) -> str:
        return self.__source

    def should_reply_json(self) -> bool:
        return False
