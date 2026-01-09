from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Dict,
    List,
)


class BaseImageSearch(ABC):
    def __init__(self, max_results: int = 50):
        self.max_results = max_results

    @abstractmethod
    def search(self, query: str) -> List[Dict[str, str]]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
