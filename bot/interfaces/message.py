from abc import (
    ABC,
    abstractmethod,
)


class AbstractMessage(ABC):
    @abstractmethod
    def get_user_id(self) -> int: ...

    @abstractmethod
    def get_username(self) -> str: ...

    @abstractmethod
    def get_text(self) -> str: ...

    @abstractmethod
    def get_chat_id(self) -> int: ...

    @abstractmethod
    def get_sender_id(self) -> int: ...

    @abstractmethod
    def get_full_name(self) -> str: ...
