from typing import (
    Dict,
    List,
)

from ddgs import DDGS

from preprocessor.characters.image_search import BaseImageSearch


class DuckDuckGoImageSearch(BaseImageSearch):
    @property
    def name(self) -> str:
        return "DuckDuckGo"

    def search(self, query: str) -> List[Dict[str, str]]:
        with DDGS() as ddgs:
            results = ddgs.images(query, max_results=self.max_results)
            return list(results)
