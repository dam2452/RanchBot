from typing import (
    Any,
    Dict,
    Iterator,
)

from serpapi import GoogleSearch

from preprocessor.services.characters.image_search.image_search import BaseImageSearch


class GoogleImageSearch(BaseImageSearch):
    def __init__(self, api_key: str, max_results: int = 50) -> None:
        super().__init__(max_results)

        if not api_key:
            raise ValueError('SerpAPI key is required for Google Image Search')

        self.__api_key = api_key

    @property
    def name(self) -> str:
        return 'Google Images (SerpAPI)'

    def search(self, query: str) -> Iterator[Dict[str, str]]:
        params = self.__build_search_params(query)
        raw_results = GoogleSearch(params).get_dict()
        yield from self.__iter_image_data(raw_results)

    def __build_search_params(self, query: str) -> Dict[str, str]:
        return {
            'engine': 'google_images',
            'q': query,
            'hl': 'pl',
            'gl': 'pl',
            'api_key': self.__api_key,
        }

    def __iter_image_data(self, raw_results: Dict[str, Any]) -> Iterator[Dict[str, str]]:
        for img in raw_results.get('images_results', [])[:self._max_results]:
            url = img.get('original') or img.get('thumbnail', '')
            if url:
                yield {'image': url, 'thumbnail': img.get('thumbnail', '')}
