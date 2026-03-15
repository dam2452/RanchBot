import random
import time
from typing import (
    Dict,
    Iterator,
)

from ddgs import DDGS

from preprocessor.services.characters.image_search.image_search import BaseImageSearch


class DuckDuckGoImageSearch(BaseImageSearch):
    def __init__(
            self,
            max_results: int = 50,
            pre_search_delay_min: float = 8.0,
            pre_search_delay_max: float = 15.0,
    ) -> None:
        super().__init__(max_results)
        self.__pre_search_delay_min = pre_search_delay_min
        self.__pre_search_delay_max = pre_search_delay_max

    @property
    def name(self) -> str:
        return 'DuckDuckGo'

    def search(self, query: str) -> Iterator[Dict[str, str]]:
        time.sleep(random.uniform(self.__pre_search_delay_min, self.__pre_search_delay_max))
        with DDGS() as ddgs:
            for r in ddgs.images(query, region='pl-pl', max_results=self._max_results):
                url = r.get('image') or r.get('thumbnail', '')
                if url:
                    yield {'image': url, 'thumbnail': r.get('thumbnail', '')}
