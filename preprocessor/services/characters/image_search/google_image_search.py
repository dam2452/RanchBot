from typing import (
    Any,
    Dict,
    List,
)

import requests

from preprocessor.services.characters.image_search.image_search import BaseImageSearch

_RAPIDAPI_HOST = 'google-search116.p.rapidapi.com'
_RAPIDAPI_URL = f'https://{_RAPIDAPI_HOST}/'


class GoogleImageSearch(BaseImageSearch):
    def __init__(self, api_key: str, max_results: int = 50) -> None:
        super().__init__(max_results)

        if not api_key:
            raise ValueError('RapidAPI key is required for Google Image Search')

        self.__api_key = api_key

    @property
    def name(self) -> str:
        return 'Google Search API (RapidAPI)'

    def search(self, query: str) -> List[Dict[str, str]]:
        raw_results = self.__call_api(query)
        return self.__extract_image_data(raw_results)

    def __call_api(self, query: str) -> Dict[str, Any]:
        headers = {
            'x-rapidapi-key': self.__api_key,
            'x-rapidapi-host': _RAPIDAPI_HOST,
        }
        params = {
            'query': query,
            'limit': str(self._max_results),
            'hl': 'pl',
            'gl': 'pl',
        }
        response = requests.get(_RAPIDAPI_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def __extract_image_data(self, raw_results: Dict[str, Any]) -> List[Dict[str, str]]:
        results = raw_results.get('results', [])[:self._max_results]
        return [
            {'image': r['url'], 'thumbnail': ''}
            for r in results
            if r.get('url')
        ]
