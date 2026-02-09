from typing import (
    Dict,
    List,
)

from serpapi import GoogleSearch

from preprocessor.characters.image_search import BaseImageSearch


class GoogleImageSearch(BaseImageSearch):
    def __init__(self, api_key: str, max_results: int = 50):
        super().__init__(max_results)
        if not api_key:
            raise ValueError("SerpAPI key is required for Google Image Search")
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "Google Images API"

    def search(self, query: str) -> List[Dict[str, str]]:
        params = {
            "engine": "google_images",
            "q": query,
            "hl": "pl",
            "gl": "pl",
            "api_key": self.api_key,
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        images = []
        for img_result in results.get("images_results", [])[:self.max_results]:
            images.append({
                "image": img_result.get("original"),
                "thumbnail": img_result.get("thumbnail"),
            })

        return images
