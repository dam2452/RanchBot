import signal
import time
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
_PAGE_TIMEOUT_MS = 12000
_LOAD_WAIT_S = 2.0
_SCROLL_STEPS = 3
_SCROLL_PAUSE_S = 1.0
_HARD_TIMEOUT_S = 25


class _SearchTimeout(Exception):
    pass


class BrowserBingImageSearch(BaseImageSearch):
    def __init__(self, browser_context: BrowserContext, max_results: int = 100) -> None:
        super().__init__(max_results)
        self.__browser_context = browser_context

    @property
    def name(self) -> str:
        return 'Bing Images (Browser)'

    def search(self, query: str) -> Iterator[Dict[str, str]]:
        yield from self.__fetch_with_timeout(query)

    def __fetch_with_timeout(self, query: str) -> List[Dict[str, str]]:
        page = self.__browser_context.new_page()
        page.set_default_timeout(_PAGE_TIMEOUT_MS)

        old_handler = signal.signal(signal.SIGALRM, self.__raise_timeout)
        signal.alarm(_HARD_TIMEOUT_S)
        try:
            url = f'{_SEARCH_URL}?q={quote(query)}&count={self._max_results}&form=HDRSC2'
            page.goto(url, wait_until='commit', timeout=_PAGE_TIMEOUT_MS)
            time.sleep(_LOAD_WAIT_S)
            self.__scroll_for_more(page)
            return self.__extract_results(page)
        except Exception:
            return []
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            try:
                page.close()
            except Exception:
                pass

    @staticmethod
    def __raise_timeout(signum: int, frame: Any) -> None:
        raise _SearchTimeout()

    @staticmethod
    def __scroll_for_more(page: Any) -> None:
        for _ in range(_SCROLL_STEPS):
            try:
                page.evaluate('window.scrollBy(0, window.innerHeight * 3)')
                time.sleep(_SCROLL_PAUSE_S)
            except Exception:
                break

    def __extract_results(self, page: Any) -> List[Dict[str, str]]:
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
        return raw[:self._max_results]
