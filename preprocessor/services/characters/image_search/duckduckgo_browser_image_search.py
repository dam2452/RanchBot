from typing import (
    Any,
    Dict,
    Iterator,
    List,
)
from urllib.parse import quote

from patchright.sync_api import BrowserContext

from preprocessor.services.characters.image_search.image_search import BaseImageSearch

_SEARCH_URL = 'https://duckduckgo.com/'
_NETWORK_IDLE_TIMEOUT = 15000
_SCROLL_STEPS = 3
_SCROLL_PAUSE_MS = 1500


class BrowserDuckDuckGoImageSearch(BaseImageSearch):
    def __init__(self, browser_context: BrowserContext, max_results: int = 100) -> None:
        super().__init__(max_results)
        self.__browser_context = browser_context

    @property
    def name(self) -> str:
        return 'DuckDuckGo Images (Browser)'

    def search(self, query: str) -> Iterator[Dict[str, str]]:
        page = self.__browser_context.new_page()
        collected: List[Dict[str, str]] = []

        def _on_response(response: Any) -> None:
            if 'duckduckgo.com/i.js' not in response.url:
                return
            try:
                body = response.json()
                for item in body.get('results', []):
                    url = item.get('image') or item.get('thumbnail', '')
                    if url:
                        collected.append({'image': url, 'thumbnail': item.get('thumbnail', '')})
            except Exception:
                pass

        page.on('response', _on_response)
        try:
            url = f'{_SEARCH_URL}?q={quote(query)}&iax=images&ia=images'
            page.goto(url, wait_until='networkidle', timeout=_NETWORK_IDLE_TIMEOUT)
            self.__scroll_for_more(page, collected)
            yield from collected[:self._max_results]
        finally:
            page.close()

    def __scroll_for_more(self, page: Any, collected: List[Dict[str, str]]) -> None:
        for _ in range(_SCROLL_STEPS):
            if len(collected) >= self._max_results:
                break
            page.evaluate('window.scrollBy(0, window.innerHeight * 3)')
            page.wait_for_timeout(_SCROLL_PAUSE_MS)
