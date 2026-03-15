from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Dict,
    Iterator,
)


class BaseImageSearch(ABC):
    def __init__(self, max_results: int = 50) -> None:
        self._max_results = max_results

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def search(self, query: str) -> Iterator[Dict[str, str]]:
        pass
