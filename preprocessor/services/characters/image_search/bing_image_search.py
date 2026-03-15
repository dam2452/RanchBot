from typing import (
    Any,
    Dict,
    Iterator,
    List,
)
from urllib.parse import quote

from patchright.sync_api import BrowserContext

from preprocessor.services.characters.image_search.image_search import BaseImageSearch

_SEARCH_URL = 'https://www.bing.com/images/search'
_RESULT_WAIT_MS = 3000
_SCROLL_STEPS = 3
_SCROLL_PAUSE_MS = 1500


class BrowserBingImageSearch(BaseImageSearch):
    def __init__(self, browser_context: BrowserContext, max_results: int = 100) -> None:
        super().__init__(max_results)
        self.__browser_context = browser_context

    @property
    def name(self) -> str:
        return 'Bing Images (Browser)'

    def search(self, query: str) -> Iterator[Dict[str, str]]:
        page = self.__browser_context.new_page()
        try:
            url = f'{_SEARCH_URL}?q={quote(query)}&count={self._max_results}&form=HDRSC2'
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(_RESULT_WAIT_MS)
            self.__scroll_to_load_more(page)
            yield from self.__extract_results(page)
        finally:
            page.close()

    @staticmethod
    def __scroll_to_load_more(page: Any) -> None:
        for _ in range(_SCROLL_STEPS):
            page.evaluate('window.scrollBy(0, window.innerHeight)')
            page.wait_for_timeout(_SCROLL_PAUSE_MS)

    def __extract_results(self, page: Any) -> Iterator[Dict[str, str]]:
        raw: List[Dict[str, str]] = page.evaluate("""() => {
            const out = [];
            for (const el of document.querySelectorAll('.iusc')) {
                try {
                    const m = JSON.parse(el.getAttribute('m') || '{}');
                    if (m.murl) out.push({image: m.murl, thumbnail: m.turl || ''});
                } catch(e) {}
            }
            if (out.length === 0) {
                for (const img of document.querySelectorAll('img.mimg, img[data-src]')) {
                    const src = img.getAttribute('data-src') || img.src || '';
                    if (src && src.startsWith('http')) out.push({image: src, thumbnail: src});
                }
            }
            return out;
        }""")
        yield from raw[:self._max_results]
