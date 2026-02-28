from typing import (
    Any,
    Dict,
    List,
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
        return 'Google Images API'

    def search(self, query: str) -> List[Dict[str, str]]:
        params = self.__build_search_params(query)
        search_client = GoogleSearch(params)
        raw_results = search_client.get_dict()

        return self.__extract_image_data(raw_results)

    def __build_search_params(self, query: str) -> Dict[str, str]:
        return {
            'engine': 'google_images',
            'q': query,
            'hl': 'pl',
            'gl': 'pl',
            'api_key': self.__api_key,
        }

    def __extract_image_data(self, raw_results: Dict[str, Any]) -> List[Dict[str, str]]:
        images: List[Dict[str, str]] = []
        image_results = raw_results.get('images_results', [])[:self._max_results]

        for img_result in image_results:
            images.append({
                'image': img_result.get('original', ''),
                'thumbnail': img_result.get('thumbnail', ''),
            })

        return images
