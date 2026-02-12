from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Dict,
    List,
)


class BaseImageSearch(ABC):

    def __init__(self, max_results: int=50) -> None:
        self.max_results = max_results

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def search(self, query: str) -> List[Dict[str, str]]:
        pass
